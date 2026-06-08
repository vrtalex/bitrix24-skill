# Catalog: commerce

Scope: sales and catalog operations.

| Method | Risk | Scope | Required | Deprecated | Docs |
|---|---|---|---|---|---|
| `sale.order.list` | read | sale |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sale/order/sale-order-list.md |
| `sale.order.add` | write | sale | fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sale/order/sale-order-add.md |
| `sale.order.update` | write | sale | id,fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sale/order/sale-order-update.md |
| `sale.payment.list` | read | sale |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sale/payment/sale-payment-list.md |
| `sale.payment.add` | write | sale | fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sale/payment/sale-payment-add.md |
| `sale.delivery.getlist` | read | sale |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sale/delivery/delivery/sale-delivery-get-list.md |
| `catalog.product.list` | read | catalog |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/catalog/product/catalog-product-list.md |
| `catalog.product.add` | write | catalog | fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/catalog/product/catalog-product-add.md |
| `catalog.product.update` | write | catalog | id,fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/catalog/product/catalog-product-update.md |
| `catalog.price.list` | read | catalog |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/catalog/price/catalog-price-list.md |
| `catalog.price.add` | write | catalog | fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/catalog/price/catalog-price-add.md |
| `sale.order.get` | read | sale | id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sale/order/sale-order-get.md |
| `sale.order.getfields` | read | sale |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sale/order/sale-order-get-fields.md |
| `sale.shipment.add` | write | sale | fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sale/shipment/sale-shipment-add.md |
| `sale.basketitem.add` | write | sale | fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sale/basket-item/sale-basket-item-add.md |
| `catalog.product.getFieldsByFilter` | read | catalog | filter |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/catalog/product/catalog-product-get-fields-by-filter.md |
| `catalog.product.get` | read | catalog | id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/catalog/product/catalog-product-get.md |
| `catalog.product.delete` | destructive | catalog | id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/catalog/product/catalog-product-delete.md |
| `catalog.product.offer.add` | write | catalog | fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/catalog/product/offer/catalog-product-offer-add.md |
| `catalog.product.offer.list` | read | catalog |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/catalog/product/offer/catalog-product-offer-list.md |
| `sale.delivery.add` | write | sale | REST_CODE,NAME,CURRENCY |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sale/delivery/delivery/sale-delivery-add.md |
| `sale.paysystem.list` | read | - |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/pay-system/sale-pay-system-list.md |
| `sale.shipmentitem.add` | write | sale | fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sale/shipment-item/sale-shipment-item-add.md |
| `sale.paymentitembasket.add` | write | sale | fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sale/payment-item-basket/sale-payment-item-basket-add.md |
| `sale.persontype.list` | read | sale |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sale/person-type/sale-person-type-list.md |
