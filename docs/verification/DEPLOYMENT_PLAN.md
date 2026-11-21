# Safe deployment plan — FERAS 2026 / Safir Holding Platform

This plan replaces a running server with the verified build on branch
`review/final-word-compliance` (commit `cf21cf6`). It is written to be executed
by a person with server access. Nothing here has been executed against the live
server: no credentials for it exist in the repository or in the agent
environment.

The plan assumes the current server already runs an older version of this same
project (Next.js + FastAPI + PostgreSQL behind Nginx). It is therefore a
**replace in place**, not a fresh install. The overriding rule is that the
database survives every step.

---

## 0. What must survive the deployment

These were built in earlier rounds and must not regress. Each one is verified
locally on the production build (see §6 for the exact evidence).

| # | Asset | Where it lives | How it is preserved |
|---|---|---|---|
| 1 | Next.js application | `frontend/` | Rebuilt from the branch; `next.config.mjs` redirects and rewrites ship with it |
| 2 | Nginx reverse proxy | `deploy/nginx.conf` | Copied over the server copy **only after** a diff is reviewed; a backup is kept |
| 3 | `/platform/*` admin routes | `frontend/app/(admin)/platform/` | Route files are part of the build; old `/dashboard`-style URLs keep redirecting |
| 4 | API fixes | `backend/app/` | Backend image rebuilt; migrations applied forward only |
| 5 | Database contents | PostgreSQL volume / server | Never dropped, never recreated, never seeded over an existing database |
| 6 | Uploaded files | `STORAGE_DIR` | Mounted volume, never overwritten by the build |

---

## 1. Pre-flight (no changes, read-only)

Run from a workstation with server access.

```bash
# 1.1 Record what the server runs today.
ssh "$SERVER" 'cd /srv/safir && git rev-parse HEAD && git status --short'
ssh "$SERVER" 'docker compose ps'
ssh "$SERVER" 'docker compose images'

# 1.2 Record the Nginx config actually in use, so the diff in §3 is real.
ssh "$SERVER" 'sudo cp /etc/nginx/conf.d/default.conf /root/nginx.conf.before'
ssh "$SERVER" 'sudo nginx -T > /root/nginx-T.before 2>&1'

# 1.3 Take a database backup. This is the rollback for every later step.
ssh "$SERVER" 'cd /srv/safir && docker compose exec -T db \
  pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > /root/safir-$(date +%F-%H%M).dump'
ssh "$SERVER" 'ls -lh /root/safir-*.dump'

# 1.4 Confirm free disk. The build needs roughly 3 GB; the dump needs its size again.
ssh "$SERVER" 'df -h / /var/lib/docker'
```

Stop and fix anything that fails here. Do not continue on a full disk or an
unverified backup.

**Backup verification** — a dump that has never been read is not a backup:

```bash
ssh "$SERVER" 'docker compose exec -T db pg_restore --list \
  < /root/safir-<stamp>.dump | head -20'
```

If that prints a table of contents, the dump is readable.

---

## 2. Stage the new build beside the old one

Deploy into a second directory so the running site is untouched until the swap.

```bash
ssh "$SERVER" 'git clone --branch review/final-word-compliance \
  https://github.com/mohammadaljallad079-rgb/feras2026.git /srv/safir-new'
ssh "$SERVER" 'cd /srv/safir-new && git rev-parse HEAD'   # must be cf21cf6 or later
```

Reuse the existing secrets and volumes. **Do not** copy `.env.example` over a
working `.env`:

```bash
ssh "$SERVER" 'cp /srv/safir/.env /srv/safir-new/.env && chmod 600 /srv/safir-new/.env'
ssh "$SERVER" 'diff <(sort /srv/safir/.env) <(sort /srv/safir-new/.env) && echo "env identical"'
```

Point the new compose file at the **existing** database volume and the existing
storage volume, so the new stack reads the same data rather than creating empty
ones. In `/srv/safir-new/docker-compose.yml`:

```yaml
volumes:
  db-data:
    external: true
    name: safir_db-data        # confirm the real name: docker volume ls
  storage:
    external: true
    name: safir_storage        # confirm the real name: docker volume ls
```

```bash
ssh "$SERVER" 'docker volume ls | grep safir'   # names must match the block above
```

---

## 3. Review the Nginx diff before replacing anything

```bash
ssh "$SERVER" 'diff /root/nginx.conf.before /srv/safir-new/deploy/nginx.conf'
```

The new file must keep, at minimum:

- `location /api/` proxied to the backend, with the `X-Forwarded-*` headers;
- `location /` proxied to the Next.js service;
- `client_max_body_size 25m` (uploads are bounded, not unlimited);
- the security headers (`X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`);
- `/health` and `/ready` exposed directly.

If the live config carries anything the repository copy lacks — a real
`server_name`, a TLS block, an extra `location` for another application on the
same host — **merge it in**. Do not overwrite the live file with the repository
copy when the live file serves more than this project.

> A second project on the same Nginx must keep its own `server` block. This plan
> only replaces the Safir `location` entries.

The routing decisions in this file are locked by
`backend/tests/test_deployment_contract.py`. Nginx could not be started in the
preparation environment (no binary, no root), so those nine checks read the
configuration and the compose file instead of proxying real traffic. They prove
the contract is intact — `/api/` to FastAPI, `/` to Next.js, probes answered
directly, forwarded and security headers present, upload ceiling bounded, and
only Nginx publishing a host port — but they cannot prove a particular server's
live config matches. That is what the diff above is for.

---

## 4. Build without stopping the running site

```bash
ssh "$SERVER" 'cd /srv/safir-new && docker compose build'
```

Building before stopping anything keeps the outage to the swap window. If the
build fails, the old site is still serving.

---

## 5. Apply migrations (forward only)

Migrations run before the new code starts, while the old site still serves.

```bash
ssh "$SERVER" 'cd /srv/safir-new && docker compose run --rm backend alembic upgrade head'
ssh "$SERVER" 'cd /srv/safir-new && docker compose run --rm backend alembic current'
```

Rules:

- Never `downgrade`. If a migration fails, stop and restore the §1.3 dump.
- Never run `scripts/seed.py` against a live database that already has data —
  it is for first install only. Seeding over live data is the one step in this
  plan that can destroy real records.
- If the server has never had the public-site CMS content, `scripts/seed_site.py`
  is safe and additive; confirm with the owner first.

---

## 6. Evidence that this build behaves as the specification requires

Recorded on a local production build (`next start`, `uvicorn`, PostgreSQL 16) at
commit `cf21cf6`:

| Check | Result |
|---|---|
| Backend suite | **389 passed, 0 failed, 0 errors, 1 skipped** (262 s) |
| Frontend lint (`lint:ci`, zero warnings) | **0 errors, 0 warnings** |
| Frontend typecheck (`tsc --noEmit`) | **clean** |
| Frontend production build | **succeeded**, all `/platform/*` routes present |
| Word-spec matrix (`scripts/check_matrix.py`) | **exit 0**, 133 tracked rows, 129 PASS, 0 FAIL |
| Responsive sweep (`check_matrix.py` route/viewport) | **85 combinations, 0 failures** |
| GitHub Actions run `44949960556` on `cf21cf6` | **Backend tests success; Lint, Typecheck, Build all success** |
| Reverse-proxy contract (`tests/test_deployment_contract.py`) | **9 checks pass**: `/api/`→FastAPI, `/`→Next.js, probes direct, forwarded + security headers, bounded upload ceiling, upstream names match compose, only Nginx publishes a port |

Opportunities section (§5.1, Table 6 R6/R7), verified against the production
build rather than the dev server:

| Function | Evidence |
|---|---|
| Six printed columns | header row reads `الموضوع، الدولة، الملف، المصدر، الحالة، السبب` (+ `إجراءات`) |
| Four decision buttons | `اعتماد`, `رفض`, `تأجيل`, `قيد المراجعة` all present on a submitted row |
| Reason mandatory on reject/defer | save button **disabled** while the reason box is empty |
| Reason enforced server-side | `POST /api/v1/opportunities/{id}/decision` → **422** `reason_required` |
| Decision persists | status and `decision_note` read back after the call |
| One decision only | a second decision returns **409** |
| Approval executes nothing (§11) | collection counts identical before and after approval |
| Exact confirmation text | «سُجل القرار. لا تحويل تلقائي للتنفيذ.» |

Routing preserved (production build, port 3000):

| Path | Result |
|---|---|
| `/` | 307 → `/ar` |
| `/ar`, `/en` | 200 |
| `/ar/solutions`, `/ar/careers`, `/ar/companies`, `/ar/about`, `/ar/privacy` | 200 |
| `/ar/service-request`, `/ar/opportunities` | 200 |
| `/platform/login`, `/platform/dashboard` | 200 |
| `/login`, `/dashboard`, `/opportunities` | 307 → `/platform/...` |
| `/api/backend/health` (Next rewrite to FastAPI) | 200 `{"status":"ok"}` |
| `/sitemap.xml` | 200 |
| `/ar/nonexistent-page` | 404 |

---

## 7. Swap

Keep the window short and reversible.

```bash
# 7.1 Stop the old stack without touching volumes.
ssh "$SERVER" 'cd /srv/safir && docker compose stop'

# 7.2 Start the new stack.
ssh "$SERVER" 'cd /srv/safir-new && docker compose up -d'

# 7.3 Wait for health, then confirm readiness.
ssh "$SERVER" 'for i in $(seq 1 30); do \
  curl -fsS http://127.0.0.1:8080/health && break; sleep 2; done'
ssh "$SERVER" 'curl -fsS http://127.0.0.1:8080/ready'
```

The new stack takes the same port, so Nginx does not change for a same-port
swap. If the new stack uses a different port, edit the upstream in
`deploy/nginx.conf`, run `sudo nginx -t`, then `sudo nginx -s reload`.

---

## 8. Post-deploy verification

Run these against the real hostname, not just localhost.

```bash
# 8.1 The site and the console answer.
curl -fsS -o /dev/null -w "root=%{http_code}\n"    https://"$DOMAIN"/
curl -fsS -o /dev/null -w "ar=%{http_code}\n"      https://"$DOMAIN"/ar
curl -fsS -o /dev/null -w "login=%{http_code}\n"   https://"$DOMAIN"/platform/login

# 8.2 The API is reached through Nginx and reports healthy.
curl -fsS https://"$DOMAIN"/api/v1/config/ai-status

# 8.3 Sign in as the owner and confirm the opportunities table renders.
#     Expected: six columns, and four decision buttons on a submitted row.
```

Then, by hand:

1. Sign in as `owner` and open `/platform/opportunities`. Confirm the six
   columns, the four buttons, and that **save stays disabled** until a reason is
   typed.
2. Reject one opportunity with a reason. Confirm the message
   «سُجل القرار. لا تحويل تلقائي للتنفيذ.» and that no project or publication
   appears anywhere afterwards.
3. Open `/platform/dashboard`, `/platform/reports`, `/platform/accounting`,
   `/platform/website` and confirm each loads with real data.
4. Export one Excel report (`/platform/accounting` → export) and open the file.
5. Open the public site in both languages and submit one test service request;
   confirm it appears under `/platform/service-requests`.
6. Confirm an old bookmark (`/dashboard`) still lands on `/platform/dashboard`.

---

## 9. Rollback

Rollback is a data decision first and a code decision second.

```bash
# 9.1 If only the code is wrong, and no migration changed the schema:
ssh "$SERVER" 'cd /srv/safir-new && docker compose down'
ssh "$SERVER" 'cd /srv/safir && docker compose up -d'

# 9.2 If a migration must be undone, restore the §1.3 dump.
#     This discards everything written since the backup — confirm with the owner.
ssh "$SERVER" 'cd /srv/safir && docker compose stop backend scheduler'
ssh "$SERVER" 'cd /srv/safir && docker compose exec -T db \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists \
  < /root/safir-<stamp>.dump'
ssh "$SERVER" 'cd /srv/safir && docker compose up -d'

# 9.3 Restore the previous Nginx config if it was replaced.
ssh "$SERVER" 'sudo cp /root/nginx.conf.before /etc/nginx/conf.d/default.conf'
ssh "$SERVER" 'sudo nginx -t && sudo nginx -s reload'
```

Because migrations are forward-only, prefer §9.1: keep the new database and run
the old code, which reads the same tables. Only use §9.2 when a migration
removed or renamed something the old code needs.

---

## 10. Configuration that must be set before go-live

These are settings, not code. The platform degrades honestly when they are
unset, and says so rather than pretending to work.

| Setting | Consequence when unset |
|---|---|
| `SECRET_KEY` | The app refuses to start |
| `DATABASE_URL` | The app refuses to start |
| `POSTGRES_PASSWORD` | Compose refuses to start |
| `CORS_ORIGINS` | Set it to the real domain; the default is localhost |
| `FRONTEND_BASE_URL` | Account emails build links to the wrong host |
| `STORAGE_DIR` | Must point at the persistent volume |
| `SMTP_*` | Mail reports "unconfigured"; account links are returned for out-of-band delivery |
| `OPENAI_API_KEY` | The assistant reports an unconfigured provider and never fabricates an answer |
| `REMINDERS_TIMEZONE` / `REMINDER_SCHEDULE_TIME` | Defaults to `Asia/Bahrain` at `07:00` |

---

## 11. What still needs a person

Three items in the brief (§12) are reserved for people and cannot be closed by
code or by a deployment:

1. **Owner approval of the public-site design.** The site is labelled
   provisional until that approval is recorded.
2. **The designer's final artwork.** Current imagery is a placeholder set.
3. **Legal review of the privacy policy.** The page is marked a draft.

Deploying does not make these true. Record the approval, the artwork handover
and the legal sign-off separately.

---

## 12. Constraints honoured while preparing this plan

| Constraint | Status |
|---|---|
| No deployment performed by the agent | Honoured — no server credentials exist here |
| No production database touched | Honoured — only local `safir_test` / `safir_e2e` and the local dev database |
| No production Docker restart | Honoured — the local stack was started with `next start` and `uvicorn`, not Compose on the server |
| No pull-request merge | Honoured — PR #2 is still a draft |
| Word specification unmodified | Honoured — both `.docx` files are unchanged |

---

## 13. ملخّص بالعربية

**ما أُنجز في هذه الجولة**

1. **قسم الفرص والاستثمار (المواصفة §5.1، الجدول 6):** تُحقّق منه على بناء الإنتاج
   لا على خادم التطوير. الأعمدة الستة المطبوعة موجودة، والأزرار الأربعة
   (اعتماد / رفض / تأجيل / قيد المراجعة) تظهر على السجل المقدَّم، وزر الحفظ
   **معطّل** حتى يُكتب السبب. الخادم يرفض بلا سبب بـ **422**، ويأبى القرار الثاني
   بـ **409**، والاعتماد **لا ينشئ** أي مشروع أو منشور: أعداد المجموعات متطابقة
   قبل الاعتماد وبعده. الرسالة الظاهرة: «سُجل القرار. لا تحويل تلقائي للتنفيذ.»
2. **ESLint:** لم يكن هناك إعداد ولا حزم، فلم يكن `next lint` يعمل أصلاً. أُضيفت
   الحزم والإعداد وسكربت `lint:ci` بصفر تحذيرات، وأُصلحت الأخطاء الستة، وأُضيفت
   خطوة Lint إلى CI. النتيجة: **0 خطأ و0 تحذير**، ونجحت الخطوة على GitHub.
3. **PR #2:** يحتوي كل التعديلات، وآخر تشغيل CI على `cf21cf6` **ناجح بالكامل**
   (اختبارات الخلفية، Lint، Typecheck، Build).
4. **مقارنة النسخة الحالية بالسيرفر:** لا توجد بيانات اعتماد للسيرفر في المستودع،
   فلم يُلمس الإنتاج. بدلاً من ذلك شُغّلت حزمة الإنتاج محلياً (Next.js production
   + FastAPI + PostgreSQL) وأُثبت أن ما يجب الحفاظ عليه يعمل: مسارات `/platform/*`،
   وإعادة توجيه الروابط القديمة، وإعادة كتابة `/api`، و`/health` و`/ready`،
   و`sitemap.xml`، وصفحات الموقع العامة بالعربية والإنجليزية.
5. **خطة النشر الآمنة:** في هذا الملف (§1–§11) — نسخ احتياطي مُتحقَّق منه، بناء
   بجانب النسخة القديمة، هجرات إلى الأمام فقط، تبديل قصير، تحقق بعد النشر، وخطة
   رجوع. القاعدة الحاكمة: **قاعدة البيانات لا تُمسّ**.

**ما يبقى بيد الإنسان (لا يُغلق بالكود)**

- اعتماد المالك لتصميم الموقع العام (الموقع مُعلَّم «مبدئي» حتى يُسجَّل الاعتماد).
- تسليم المصمم للأعمال الفنية النهائية (الصور الحالية بدائل).
- المراجعة القانونية لسياسة الخصوصية (الصفحة مُعلَّمة «مسودة»).

**ما لم يُنفَّذ ولماذا**

- **لم يُنشر شيء على السيرفر.** لا يوجد وصول SSH ولا بيانات اعتماد في المستودع،
  ولم يُطلب مني تجاوز ذلك. خطة النشر جاهزة لشخص يملك الوصول.
- **لم يُدمج PR #2.** ما زال مسودة كما كان.

---
