# Chains: core

## 1) Lead intake and qualification
1. `crm.item.fields` with `entityTypeId=1` — discover required fields first (they vary per portal)
2. `crm.item.add` with `entityTypeId=1`
3. `crm.item.list` with `entityTypeId=1` (verify; for real de-dup use chain 4)
4. `crm.item.update` with `entityTypeId=1` (score, owner, comment)

Guardrails:
- use `--confirm-write`; keep a deterministic `filter` for list checks
- phone/email: universal `crm.item.*` uses an `fm` array of `{typeId,valueType,value}`; classic `crm.lead.*`/`crm.contact.*` use `PHONE`/`EMAIL` multifield arrays of `{VALUE,VALUE_TYPE}`
- universal CRM uses `entityTypeId` (1=lead, 2=deal, 3=contact, 4=company); legacy entity methods are deprecated

## 2) Deal change to task assignment
1. `crm.item.list` with `entityTypeId=2` (deal) and a stage filter
2. `tasks.task.add` linked to the deal (bind it via chain 6)
3. `crm.item.update` with `entityTypeId=2` and the task reference

## 3) Event bootstrap for reliable sync
1. `event.bind` for the chosen CRM event
2. `event.offline.list`
3. `event.offline.get` with safe processing
4. `event.offline.clear` only after successful persist

Guardrails:
- offline events require OAuth application auth (a webhook gets WRONG_AUTH_TYPE)
- an offline ONCRM*UPDATE handler that writes back via `crm.item.update` re-queues its own event — pass the same auth_connector on the bind, every write-back, and the get to suppress self-events
- gate the reserve/confirm mode (clear=0 + process_id) behind `feature.get` with code rest_offline_extended

## 4) De-duplicate before creating (lead lookup / click-to-call card)
1. `crm.duplicate.findbycomm` with `type='PHONE'`, `values=[phone]` (repeat with `type='EMAIL'`); result is grouped LEAD/CONTACT/COMPANY
2. `crm.item.list` (entityTypeId 1/3/4) with a `filter` by the found ids to load matches
3. `crm.item.add` only if there is no match; else link the new item to the found contact/company id

## 5) Log an activity and a comment on a record
1. `crm.enum.ownertype` — resolve the owner-type constant (1=lead, 2=deal, 3=contact)
2. `crm.activity.todo.add` with `ownerTypeId`, `ownerId`, `deadline` (the modern activity; the older crm.activity.add is deprecated)
3. `crm.timeline.comment.add` for a free-text note
4. `crm.activity.list` to verify

## 6) Create a task linked to a CRM element
1. `crm.enum.ownertype` — get the `SYMBOL_CODE_SHORT` (e.g. D=deal, L=lead, Tb*=smart-process)
2. `crm.item.list` to get the element id
3. `tasks.task.add` with `fields.UF_CRM_TASK = ['<SYMBOL_CODE_SHORT>_<id>']` (e.g. D_42)
4. `tasks.task.get` selecting `UF_CRM_TASK` to confirm

## 7) Resolve a deal stage by name and advance it
1. `crm.category.list` with `entityTypeId=2` — get the funnel/category id (stage names are never stored on the item)
2. `crm.status.list` filter by `ENTITY_ID` like `DEAL_STAGE_<categoryId>` — map stage name to `STATUS_ID`; read `EXTRA.SEMANTICS` for won/lost
3. `crm.item.update` with `entityTypeId=2` and the resolved `stageId`

## 8) Attach products with tax/discount to a deal
1. `catalog.product.list` (load the `commerce` pack too) to pick a product
2. `crm.item.add` with `entityTypeId=2` (deal)
3. `crm.item.productrow.set` with `ownerType`, `ownerId`, and `productRows` of `{productId, price, quantity, taxRate, taxIncluded, discountSum, discountTypeId}` (replaces the whole set)

## 9) Bulk export with batch + pagination
1. `crm.item.list` with a `filter` like `{">=updatedTime": lastSync}`, deterministic order; read `total`
2. page with `start` advancing by 50 (fixed page size) until exhausted
3. wrap up to 50 list/read calls in one `batch` (one rate tick); on QUERY_LIMIT_EXCEEDED (503) / OPERATION_TIME_LIMIT (429) back off; upsert downstream idempotently
