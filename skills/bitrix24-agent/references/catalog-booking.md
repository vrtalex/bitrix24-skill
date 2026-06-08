# Catalog: booking

Scope: bookings, resources, slots.

| Method | Risk | Scope | Required | Deprecated | Docs |
|---|---|---|---|---|---|
| `booking.v1.booking.list` | read | booking |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/booking/booking/booking-v1-booking-list.md |
| `booking.v1.booking.get` | read | booking | id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/booking/booking/booking-v1-booking-get.md |
| `booking.v1.booking.add` | write | booking | fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/booking/booking/booking-v1-booking-add.md |
| `booking.v1.booking.update` | write | booking | id,fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/booking/booking/booking-v1-booking-update.md |
| `booking.v1.booking.delete` | destructive | booking | id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/booking/booking/booking-v1-booking-delete.md |
| `booking.v1.booking.client.list` | read | booking | bookingId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/booking/booking/client/booking-v1-booking-client-list.md |
| `booking.v1.booking.client.set` | write | booking | bookingId,clients |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/booking/booking/client/booking-v1-booking-client-set.md |
| `booking.v1.resource.list` | read | booking |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/booking/resource/booking-v1-resource-list.md |
| `booking.v1.resource.get` | read | booking | id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/booking/resource/booking-v1-resource-get.md |
| `booking.v1.resource.add` | write | booking | fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/booking/resource/booking-v1-resource-add.md |
| `booking.v1.resource.update` | write | booking | id,fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/booking/resource/booking-v1-resource-update.md |
| `booking.v1.resource.delete` | destructive | booking | id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/booking/resource/booking-v1-resource-delete.md |
| `booking.v1.resource.slots.list` | read | booking | resourceId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/booking/resource/slots/booking-v1-resource-slots-list.md |
| `booking.v1.resource.slots.set` | write | booking | resourceId,slots |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/booking/resource/slots/booking-v1-resource-slots-set.md |
| `booking.v1.clienttype.list` | read | booking |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/booking/booking-v1-clienttype-list.md |
