# Catalog: services

Scope: booking, calendar, and time-management.

| Method | Risk | Scope | Required | Deprecated | Docs |
|---|---|---|---|---|---|
| `booking.v1.booking.list` | read | booking |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/booking/booking/booking-v1-booking-list.md |
| `booking.v1.booking.add` | write | booking | fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/booking/booking/booking-v1-booking-add.md |
| `booking.v1.booking.update` | write | booking | id,fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/booking/booking/booking-v1-booking-update.md |
| `booking.v1.resource.list` | read | booking |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/booking/resource/booking-v1-resource-list.md |
| `calendar.event.get` | read | calendar | type,ownerId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/calendar/calendar-event/calendar-event-get.md |
| `calendar.event.add` | write | calendar | type,ownerId,from,to,section,name,attendees,host |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/calendar/calendar-event/calendar-event-add.md |
| `calendar.event.update` | write | calendar | id,type,ownerId,name,attendees,host |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/calendar/calendar-event/calendar-event-update.md |
| `calendar.section.get` | read | calendar | type,ownerId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/calendar/calendar-section-get.md |
| `timeman.status` | read | timeman |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/timeman/base/timeman-status.md |
| `timeman.open` | write | timeman |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/timeman/base/timeman-open.md |
| `timeman.close` | write | timeman |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/timeman/base/timeman-close.md |
| `calendar.event.delete` | destructive | calendar | id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/calendar/calendar-event/calendar-event-delete.md |
| `calendar.section.add` | write | calendar | type,ownerId,name |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/calendar/calendar-section-add.md |
