# Review of harbor at 7a9f10e84d87 (against base 4ef35ce00779, a snapshot of HEAD 4ef35ce00779)

Reviewers produced 18 findings, grouped into 13 issues. 12 issues were verified against the code, and 10 were confirmed.

| Severity | Issues | Verified | Confirmed |
| -- | --: | --: | --: |
| Critical | 1 | 1 | 1 |
| High | 11 | 11 | 9 |
| Medium | 1 | 0 | 0 |
| Low | 0 | 0 | 0 |

Confirmed issues carrying each category label, where one issue can carry several:

| Category | Confirmed issues |
| -- | --: |
| security | 5 |
| correctness | 3 |
| performance | 2 |
| architecture | 1 |
| testing | 1 |

## Confirmed

| ID | Severity | Second check | Location | Title |
| -- | -- | -- | -- | -- |
| I0001 | Critical | Critical | `src/git-auth.ts:8` | gitAuthArgs substring host check leaks service token to attacker hosts via cloneRepo |
| I0003 | High |  | `src/routes.ts:21` | Repository id used as directory path without validation, allowing directory escape |
| I0004 | High | High | `src/store.ts:29` | Store.deleteRepo lets non-admins delete system-owned repositories |
| I0007 | High |  | `src/config.ts:3` | ADMIN_CIDR 0.0.0.0/0 makes every client an admin for auditLog |
| I0012 | High |  | `src/tasks.ts:16` | createFixTask writes feedback separately, so poll and emit see null feedback |
| I0002 | Medium |  | `src/api.ts:27` | loadDashboard does not handle rejection from fetchCurrentUser, so the dashboard never renders |
| I0006 | Medium |  | `src/ci.ts:4` | getBuild CI request has no timeout or abort signal |
| I0008 | Medium |  | `src/crypto.ts:10` | No tests for encrypt/decrypt round trip and tamper detection in crypto.ts |
| I0009 | Medium |  | `src/jira.ts:4` | getIssue Jira request has no timeout or abort signal |
| I0010 | Medium |  | `src/jira.ts:9` | searchAssigned interpolates unescaped email into JQL query |

## Refuted or unverifiable

| ID | Basis | Reason |
| -- | -- | -- |
| I0005 | refuted | The claim does not match the code. `fetchUserList` in src/api.ts (lines 16-24) does not throw on a non-2xx response. Line 19 checks `res.ok` and returns an empty array when the status is not 2xx. The whole body is also inside a try/catch (lines 17 and 21-23) that returns `[]` for network errors and  |
| I0011 | refuted | The claim does not match the code. In src/store.ts:21, Store.findByName calls this.db.query with a constant SQL string that uses a `?` placeholder, and passes `name` separately in the params array ([name]). It does not concatenate or interpolate `name` into the SQL text. The Db interface (src/store. |

## Coverage

11 files in scope.
Area files present: architecture, correctness, performance, security, testing.
- `src/api.ts`
- `src/ci.ts`
- `src/config.ts`
- `src/crypto.ts`
- `src/dashboard.ts`
- `src/git-auth.ts`
- `src/jira.ts`
- `src/routes.ts`
- `src/store.ts`
- `src/tasks.ts`
- `src/worktree.ts`
