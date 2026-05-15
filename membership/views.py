from datetime import timedelta

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods

from profiles.models import UserProfile
from .tiers import comparison_rows


def _activate_pro(user, days=365, stripe_customer=None):
    profile, _created = UserProfile.objects.get_or_create(user=user)
    profile.pro_tier = 'pro'
    profile.pro_until = timezone.now() + timedelta(days=days)
    if not profile.pro_started_at:
        profile.pro_started_at = timezone.now()
    if stripe_customer:
        profile.stripe_customer_id = stripe_customer[:64]
    profile.save()


def _deactivate_pro(user):
    profile, _created = UserProfile.objects.get_or_create(user=user)
    profile.pro_tier = ''
    profile.pro_until = None
    profile.stripe_customer_id = ''
    profile.ai_assist_date = None
    profile.ai_assist_count = 0
    profile.save()


def _billing_period(request):
    p = (request.GET.get('billing') or 'monthly').lower()
    if p not in ('monthly', 'yearly'):
        p = 'monthly'
    return p


def _pro_days_for_billing(billing: str) -> int:
    return 365 if billing == 'yearly' else 30


def _stripe_checkout_mode(price_id: str) -> str:
    """Рекуррентные Price в Stripe требуют mode=subscription, разовые — mode=payment."""
    pid = (price_id or '').strip()
    if not pid or not getattr(settings, 'STRIPE_SECRET_KEY', ''):
        return 'payment'
    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        pri = stripe.Price.retrieve(pid)
        if getattr(pri, 'recurring', None) and pri.recurring:
            return 'subscription'
    except stripe.error.StripeError:
        pass
    return 'payment'


def _checkout_session_grants_pro(session) -> bool:
    """Успешный Checkout: StripeObject (retrieve) или dict (webhook)."""
    def _get(key):
        if isinstance(session, dict):
            return session.get(key)
        return getattr(session, key, None)

    if _get('status') != 'complete':
        return False
    if _get('mode') == 'subscription':
        return bool(_get('subscription'))
    return _get('payment_status') == 'paid'


def _format_money_minor(unit_amount: int | None, currency: str | None) -> str:
    if unit_amount is None:
        return ''
    cur = (currency or 'usd').upper()
    amt = unit_amount / 100.0
    if amt == int(amt):
        return f'{int(amt)} {cur}'
    return f'{amt:.2f} {cur}'


def _format_money_float(amount: float, currency: str | None) -> str:
    cur = (currency or 'usd').upper()
    rounded = round(amount, 2)
    s = f'{rounded:.2f}'.rstrip('0').rstrip('.')
    return f'{s} {cur}'


def _stripe_yearly_toggle_and_footer(price_id: str) -> tuple[str | None, str | None]:
    """
    Годовая цена в Stripe = полная сумма за период (например 42 USD).
    Возвращает (подпись «в месяц» для тумблера, полная сумма за год для футера).
    """
    pid = (price_id or '').strip()
    if not pid or not getattr(settings, 'STRIPE_SECRET_KEY', ''):
        return None, None
    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        p = stripe.Price.retrieve(pid)
        ua = p.unit_amount
        if ua is None:
            return None, None
        cur = p.currency
        rec = getattr(p, 'recurring', None)
        interval = getattr(rec, 'interval', None) if rec is not None else None

        total_major = ua / 100.0
        footer = _format_money_minor(ua, cur)

        if interval == 'month':
            # Неверный тип цены в годовом слоте — показываем как пришло из Stripe
            lbl = _stripe_price_label(pid)
            return lbl, lbl

        # Годовая подписка или разовый платёж за год: эквивалент /12
        per_month = total_major / 12.0
        toggle = _format_money_float(per_month, cur) + ' / ' + _('мес.')
        return toggle, footer
    except stripe.error.StripeError:
        return None, None


def _stripe_price_label(price_id: str) -> str | None:
    """Подпись цены для UI (Stripe Price id)."""
    pid = (price_id or '').strip()
    if not pid or not getattr(settings, 'STRIPE_SECRET_KEY', ''):
        return None
    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        p = stripe.Price.retrieve(pid)
        base = _format_money_minor(p.unit_amount, p.currency)
        if not base:
            return None
        rec = getattr(p, 'recurring', None)
        interval = getattr(rec, 'interval', None) if rec is not None else None
        if interval == 'month':
            return f'{base} / ' + _('мес.')
        if interval == 'year':
            return f'{base} / ' + _('год')
        return base
    except stripe.error.StripeError:
        return None


def _stripe_setup_issues(monthly_id: str, yearly_id: str) -> list[str]:
    """Короткие подсказки, чего не хватает для checkout (для отладки)."""
    issues: list[str] = []
    sk = getattr(settings, 'STRIPE_SECRET_KEY', '') or ''
    if not sk:
        issues.append(_('В .env нет STRIPE_SECRET_KEY (секретный ключ, sk_test_… или sk_live_…).'))
    elif not sk.startswith(('sk_test_', 'sk_live_')):
        issues.append(_('STRIPE_SECRET_KEY должен начинаться с sk_test_ или sk_live_ (не путайте с publishable pk_…).'))
    mid = (monthly_id or '').strip()
    if not mid:
        issues.append(
            _('Нужен Price ID месячного тарифа: STRIPE_PRICE_PRO или STRIPE_PRICE_PRO_MONTHLY (значение price_… из Stripe Dashboard).'),
        )
    elif not mid.startswith('price_'):
        issues.append(_('Price ID должен выглядеть как price_… (Product → Prices в Stripe).'))
    yid = (yearly_id or '').strip()
    if yid and not yid.startswith('price_'):
        issues.append(_('Годовой STRIPE_PRICE_PRO_YEARLY должен быть price_…'))
    return issues


@require_http_methods(['GET'])
def membership_plans(request):
    rows = comparison_rows()
    is_pro = False
    if request.user.is_authenticated:
        profile, _created = UserProfile.objects.get_or_create(user=request.user)
        is_pro = profile.is_pro

    billing_period = _billing_period(request)
    monthly_id = getattr(settings, 'STRIPE_PRICE_PRO_MONTHLY', '') or getattr(
        settings, 'STRIPE_PRICE_PRO', '',
    )
    yearly_id = getattr(settings, 'STRIPE_PRICE_PRO_YEARLY', '')
    if billing_period == 'yearly' and not yearly_id:
        billing_period = 'monthly'

    stripe_ready = bool(settings.STRIPE_SECRET_KEY and monthly_id)
    yearly_ready = bool(yearly_id)
    price_monthly_display = _stripe_price_label(monthly_id) if monthly_id else None
    price_yearly_toggle_display, price_yearly_footer_display = _stripe_yearly_toggle_and_footer(
        yearly_id,
    )
    selected_price_display = (
        price_yearly_footer_display if billing_period == 'yearly' else price_monthly_display
    )
    stripe_setup_issues = [] if stripe_ready else _stripe_setup_issues(monthly_id, yearly_id)

    return render(request, 'membership/plans.html', {
        'comparison': rows,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
        'show_test_button': settings.PRO_TEST_BUTTON,
        'stripe_configured': stripe_ready,
        'yearly_available': yearly_ready,
        'billing_period': billing_period,
        'is_pro': is_pro,
        'price_monthly_display': price_monthly_display,
        'price_yearly_toggle_display': price_yearly_toggle_display,
        'price_yearly_footer_display': price_yearly_footer_display,
        'selected_price_display': selected_price_display,
        'stripe_setup_issues': stripe_setup_issues,
    })


@login_required
def checkout(request):
    monthly_id = getattr(settings, 'STRIPE_PRICE_PRO_MONTHLY', '') or getattr(
        settings, 'STRIPE_PRICE_PRO', '',
    )
    yearly_id = getattr(settings, 'STRIPE_PRICE_PRO_YEARLY', '')

    billing = _billing_period(request)
    if billing == 'yearly':
        price_id = yearly_id
        if not price_id:
            billing = 'monthly'
            price_id = monthly_id
    else:
        price_id = monthly_id

    if not settings.STRIPE_SECRET_KEY or not price_id:
        messages.error(
            request,
            _(
                'Оплата не настроена. Добавьте STRIPE_SECRET_KEY и price ID '
                '(STRIPE_PRICE_PRO_MONTHLY / STRIPE_PRICE_PRO или STRIPE_PRICE_PRO_YEARLY) в .env',
            ),
        )
        return redirect('membership:plans')

    stripe.api_key = settings.STRIPE_SECRET_KEY
    success = request.build_absolute_uri(reverse('membership:success'))
    cancel = request.build_absolute_uri(reverse('membership:canceled'))
    mode = _stripe_checkout_mode(price_id)
    try:
        session = stripe.checkout.Session.create(
            mode=mode,
            line_items=[{'price': price_id, 'quantity': 1}],
            success_url=success + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=cancel,
            client_reference_id=str(request.user.id),
            customer_email=request.user.email or None,
            metadata={
                'user_id': str(request.user.id),
                'billing': billing,
            },
        )
    except stripe.error.StripeError as e:
        messages.error(request, str(e.user_message or e))
        return redirect('membership:plans')

    return redirect(session.url, code=303)


@login_required
def success(request):
    session_id = request.GET.get('session_id')
    if session_id and settings.STRIPE_SECRET_KEY:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if _checkout_session_grants_pro(session):
                uid = session.client_reference_id or session.metadata.get('user_id')
                if uid and str(request.user.id) == str(uid):
                    cust = session.customer or ''
                    if isinstance(cust, str):
                        cust_id = cust
                    else:
                        cust_id = getattr(cust, 'id', '') or ''
                    meta = session.metadata or {}
                    billing = (meta.get('billing') or 'monthly').lower()
                    if billing not in ('monthly', 'yearly'):
                        billing = 'monthly'
                    days = _pro_days_for_billing(billing)
                    _activate_pro(request.user, days=days, stripe_customer=cust_id or None)
                    messages.success(request, _('Добро пожаловать в Pro!'))
        except stripe.error.StripeError:
            messages.info(
                request,
                _('Если оплата прошла успешно, статус обновится через минуту.'),
            )
    else:
        messages.success(request, _('Спасибо!'))
    return redirect('membership:plans')


def canceled(request):
    messages.info(request, _('Оплата отменена.'))
    return redirect('membership:plans')


@csrf_exempt
@require_POST
def stripe_webhook(request):
    secret = settings.STRIPE_WEBHOOK_SECRET
    if not secret or not settings.STRIPE_SECRET_KEY:
        return HttpResponse(status=400)
    stripe.api_key = settings.STRIPE_SECRET_KEY
    payload = request.body
    sig = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    try:
        event = stripe.Webhook.construct_event(payload, sig, secret)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        uid = session.get('client_reference_id') or (session.get('metadata') or {}).get('user_id')
        if uid and _checkout_session_grants_pro(session):
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(pk=int(uid))
                cust = session.get('customer') or ''
                meta = session.get('metadata') or {}
                billing = (meta.get('billing') or 'monthly').lower()
                if billing not in ('monthly', 'yearly'):
                    billing = 'monthly'
                days = _pro_days_for_billing(billing)
                _activate_pro(
                    user,
                    days=days,
                    stripe_customer=str(cust) if cust else None,
                )
            except (User.DoesNotExist, ValueError, TypeError):
                pass

    return HttpResponse(status=200)


@login_required
@require_POST
def test_activate_pro(request):
    if not settings.PRO_TEST_BUTTON:
        return HttpResponseForbidden()
    _activate_pro(request.user, days=3650)
    messages.success(request, _('Тест: Pro активирован бесплатно.'))
    return redirect('membership:plans')


@login_required
@require_POST
def test_deactivate_pro(request):
    if not settings.PRO_TEST_BUTTON:
        return HttpResponseForbidden()
    _deactivate_pro(request.user)
    messages.success(request, _('Тест: Pro отключён.'))
    return redirect('membership:plans')
