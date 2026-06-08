# Chains: commerce

## 1) Order intake to payment

You CANNOT add a product to an order directly — line items go through the basket.

1. `sale.persontype.list` to pick a `personTypeId`
2. `sale.order.add` with `fields` { lid, personTypeId, currency }
3. `sale.basketitem.add` per line with `fields` { orderId, productId, quantity, price }
4. `sale.payment.add` with `fields` { orderId, sum, paySystemId }; `sale.paymentitembasket.add` to bind paid lines
5. `sale.shipment.add` then `sale.shipmentitem.add` to bind shipped lines
6. `sale.order.get` to verify totals

Guardrails:
- all `sale.*` are admin-only, scope `sale`, with params wrapped in a `fields` object
- use `--confirm-write`; verify the order total after binding basket/payment/shipment items

## 2) Product and price sync

1. `catalog.product.list`
2. `catalog.price.list`
3. `catalog.product.update` or `catalog.price.add`

## 3) Delivery assignment

1. `sale.delivery.getlist`
2. choose delivery service id
3. update order shipment/payment context
