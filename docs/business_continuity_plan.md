# Business Continuity Plan — RestaurantFlow

**Version:** 1.0  
**Effective from:** Phase 25

---

## Scenario 1: POS Terminal Offline

### Impact
- Branch cannot process new orders via the digital POS
- Affects customer order flow at the counter

### Immediate Mitigation
- Switch to manual order taking using printed order forms
- Notify kitchen verbally or via paper tickets
- Continue accepting cash payments
- If the terminal is a tablet, attempt restart and reconnect to the application network

### Manual Fallback Procedure
1. Use printed order pads and bill templates (kept at each counter)
2. Manually calculate totals using a calculator
3. Record all orders on paper with timestamp, items, and amount
4. Keep paper records for later reconciliation

### Recovery Steps
1. Diagnose: network issue vs. application issue vs. hardware
2. If network: check router/switch at branch
3. If application: check `/health/live/` from another device
4. If hardware: replace terminal device or use a backup tablet
5. After recovery: enter all paper orders into the system for reconciliation

### Communication Plan
- Branch manager notifies Central Operations via phone
- Central Operations creates a CentralIssue: `COUNTER_SESSION_EXCEPTION`
- Update customers about brief delay

---

## Scenario 2: Internet Connection Down at Branch

### Impact
- POS cannot communicate with central application
- Payment processing via card terminal fails
- Real-time kitchen display may fail if cloud-hosted
- Reporting to central unavailable

### Immediate Mitigation
- Accept cash payments only
- Use offline receipt printer if available
- Continue operations using local network if any services are deployed locally
- Inform customers of card payment unavailability

### Manual Fallback Procedure
1. All orders: manual paper recording (see Scenario 1)
2. Cash only: enforce minimum cash float policy
3. Estimate bill totals using price list printout posted at counter

### Recovery Steps
1. Contact ISP for outage information and estimated restoration
2. If outage > 2 hours: consider mobile hotspot as backup connection
3. After restoration: sync any offline transactions to central system
4. Reconcile paper records with digital system

### Communication Plan
- Branch manager notifies Central Operations immediately
- Operations records downtime start/end time
- If > 4 hours, escalate to management

---

## Scenario 3: Payment Processing Unavailable

### Impact
- Card and digital payments cannot be processed
- Orders can still be taken but payment collection is limited
- May affect end-of-day reconciliation

### Immediate Mitigation
- Accept cash only
- Post "Card payments unavailable" notice at entrance
- For large orders (pre-approved): issue invoice for later payment

### Manual Fallback Procedure
1. Record all cash payments manually
2. Issue paper receipts (numbered, with branch stamp)
3. For pre-approved credit: record name, phone, and amount for follow-up

### Recovery Steps
1. Check payment provider status page
2. Check network connectivity to payment gateway
3. If provider-side: wait for restoration; no action needed
4. If configuration issue: check `PAYMENT_GATEWAY_API_KEY` and service settings in admin
5. After restoration: reconcile any delayed transactions

### Communication Plan
- Alert sent via CentralAlert: `PAYMENT_EXCEPTION`
- Notify customers at counter
- Operations manager monitors status page

---

## Scenario 4: Kitchen Display System Down

### Impact
- Kitchen cannot see incoming orders on the digital display
- Order preparation depends on verbal communication with counter staff

### Immediate Mitigation
- Counter staff prints order tickets (if printer available)
- Counter staff verbally relays orders to kitchen
- Kitchen uses paper tickets taped to preparation station

### Manual Fallback Procedure
1. Counter prints or handwrites order tickets
2. Kitchen acknowledges each order verbally
3. Mark "READY" on paper ticket when complete
4. Counter staff monitors kitchen pickup area

### Recovery Steps
1. Check KDS device connectivity and power
2. Check application: `/api/kitchen/orders/` via browser or Postman
3. If software issue: restart kitchen display client
4. If hardware issue: use a secondary tablet or phone with kitchen app
5. If application issue: restart `restaurantflow_app` container after checking logs

### Communication Plan
- Branch manager coordinates kitchen-counter communication
- If > 1 hour: consider reducing menu to simpler items
- CentralAlert: `KITCHEN_BACKLOG` will fire if orders queue up

---

## Scenario 5: Central Database Down

### Impact
- All branches lose application access simultaneously
- No new orders can be processed
- All digital payments fail
- Central reporting and monitoring unavailable

### Immediate Mitigation
- Activate all-branch manual operations (see Scenarios 1–3 for each branch)
- Notify all branch managers simultaneously via phone/messaging app
- Set a manual queue limit per branch to avoid overwhelming kitchen

### Manual Fallback Procedure
1. Each branch operates independently with paper records
2. Establish a check-in call with all branch managers every 30 minutes
3. Prioritize cash-only operations

### Recovery Steps
Follow the Database Recovery Runbook (`docs/disaster_recovery_runbook.md`, Scenario 1):
1. Diagnose database container status
2. Attempt restart if crash (no corruption)
3. Restore from latest backup if data loss
4. Run migrations after restore
5. Restart application
6. Notify all branches when system is restored

### Communication Plan
- Automated: CentralAlert fires for all branches simultaneously
- Manual: Operations team calls all branch managers
- Customer notification: post "System maintenance" on social media if > 1 hour

### Estimated RTO: 1–4 hours

---

## Scenario 6: Branch Server Down

### Impact
- Affects a single branch only
- Central operations continue; other branches unaffected

### Immediate Mitigation
- Branch switches to manual operations (Scenarios 1–3)
- Other branches are unaffected

### Recovery Steps
1. If Docker container crashed: `docker compose restart restaurantflow_app`
2. If host server down: provision replacement server, deploy from configuration
3. After restoration: sync any offline data accumulated during downtime

### Communication Plan
- Branch manager notifies Central Operations
- Central Operations creates a CentralIssue
- Estimated resolution time communicated to branch

---

## Scenario 7: Central Control System Down

### Impact
- Operators cannot see CentralAlerts or CentralIssues
- Branch-level operations continue normally (Central Control is monitoring only)
- Automatic alert escalations stop working

### Immediate Mitigation
- Branches continue operating normally — Central Control is a monitoring tool, not an operational dependency
- Operations staff fall back to direct application monitoring (health endpoints, Grafana)

### Recovery Steps
1. Check application logs for errors in `central_control` or `notifications` apps
2. Run `python manage.py check` for configuration issues
3. Restart application container: `docker restart restaurantflow_app`
4. Verify Central Control dashboard loads and shows current data

### Communication Plan
- System Administrator handles recovery
- Operations managers use alternative monitoring during outage (health endpoints, Grafana dashboards)
- No customer impact expected

### Estimated RTO: 15–60 minutes
