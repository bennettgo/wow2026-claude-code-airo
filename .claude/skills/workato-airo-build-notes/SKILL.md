---
name: workato-airo-build-notes
description: Hard-won gotchas for building Workato assets through the AIRO MCP and Dev API MCP, covering skill creation, MCP server attachment, token minting, testing, job logs, verifying a skill's actual return data, and data-table-backed skills. Use whenever creating or debugging a Workato Skill, MCP server, Genie, or recipe through an MCP tool, whenever verifying that a skill returns correct data, or when an AIRO call fails in a way the error message does not explain.
---

# Workato AIRO build notes

Things that cost time to discover. Each was verified against a live workspace, with the date noted.

## Know which workspace your MCP actually points at

Several Workato MCP servers can be connected at once and they do **not** all reach the same workspace. Check before concluding an asset is missing.

Verified 2026-09-18:

| MCP server | Endpoint | Workspace |
|---|---|---|
| `workato-airo-mcp-preview` | `app.preview.workato.com/airo_mcp` | IDEA Lifestyle Customer Data & Personalization, 325807, root 577822 |
| `workato-dev-api-preview` | `app.preview.workato.com/mcp` | same, 325807 |
| `workato-airo-mcp-server` | `app.workato.com/airo_mcp` | IDEA Supplier Management |
| `workato-dev-api` | `app.workato.com/mcp` | IDEA Supplier Management |

Corrected 2026-09-19. An earlier version of this table called the preview
workspace "PE Copilot preview". It is 325807, and `GET /api/users/me` on the
preview Dev API token confirms it.

A 404 from `mcp_server_get`, or `recipe_list` returning 0 for a folder you can see in the UI, usually means wrong endpoint rather than deleted asset. Confirm with `get_users_me` (Dev API) or `folder_list`, and compare root folder IDs.

## Creating a skill-triggered recipe

A recipe using the `workato_skill` trigger needs an explicit `"config": "[]"` field at creation, **when creating it through the raw Dev API path**. Without it the recipe is created but cannot be started, and the error is `missing adapter configuration: workato_skill`, which does not point at the missing field.

Corrected 2026-09-20: this does not apply to the `workspace_init`/`workspace_push` lifecycle on `workato-airo-mcp-preview`. Passing `config=[]` there is rejected outright (`Input field 'config' not found in schema`, code `extended_schema_input_loss`). Omit it; that lifecycle handles it internally. Only add it back if you're building through the older raw-Dev-API recipe-creation path this note originally described.

Also on this lifecycle: a skill's parameters live under the trigger variable, not top-level. If the trigger step is named `trigger_1`, read the input with `trigger_1['parameters']['case_number']`, not `parameters['case_number']`. `recipe.datapill.list` will show you the real path if you're not sure.

## "Folder not found" on push when the folder plainly exists

If `workspace_push` fails with `Folder with id 'NNN' was not found` while `folder.list` and `project.list` both return that folder, it is a project grant gap, not a missing folder. The read path and the write path use different authorization. Verified 2026-09-19: folder `583790` listed fine and refused every push, while `578470` accepted one immediately.

Confirm it rather than guessing, with the Dev API:

```
GET /api/projects/{project_id}/project_grants
```

It returns every grant on the project with the role and the user. Compare a
project that accepts your pushes against the one that refuses them. Verified
2026-09-19: project `552603` listed the pushing user as Project admin and
accepted pushes, project `555710` listed a different person as its only grant
and refused every one.

Fix it by granting the pushing identity access to that project. Do not work around it by building somewhere else and moving assets later.

## Pushing a skill-triggered recipe converts it automatically

`workspace_push` on a recipe whose trigger is `workato_skill` returns both the recipe ID and a `skl-*` handle, already converted. Verified 2026-09-19: recipe `1874274` came back with `skl-Abe89XRW-Ct3w3E-B6` from the push alone.

The separate `recipe_builder_convert_to_skill` step is only needed when a recipe was created some other way, for example by the older recipe-builder flow or the migration script.

## Attaching skills to an MCP server

Convert the recipe to a Skill first, then attach it by its `skl-*` handle:

```json
{"trigger_application": "workato_skill", "id": "skl-XXXX-XXXX-XX"}
```

Attaching by raw numeric recipe ID fails MCP server creation with `invalid asset`. Recipe IDs work for `workato_recipe_function` and `workato_api_platform` tools, but not for skill-triggered ones.

## Minting an MCP server token

`POST /mcp/mcp_servers/{handle}/tokens` returns `plain_token` directly in a flat response. There is no separate renew call to make afterwards.

## Testing a skill

`test_recipe` and `test_recipe_input_schema` exist **only on the preview AIRO MCP**. The production AIRO MCP can run saved test cases but cannot test a skill ad hoc.

Skills have no pollable trigger, so `test_recipe` needs a `trigger_event`. Call `test_recipe_input_schema` first: it returns the required fields and a ready-to-paste sample. The event covers the whole trigger output, so it includes a `context` object (genie_id, conversation_id, user_email and so on) that the skill itself never declares.

## Reading job logs

Verified 2026-09-18 on recipe 1860936:

- **`get_recipe_test_status` lies, sometimes.** It reported `NO_TEST_RUN` while the test job had already run and succeeded. Go to the job list instead when you need a trustworthy answer.
- `recipe.job.list` prints `handle=<unavailable>`, but its `internal_id` works as the `--job-id` argument to `recipe.job.get`.

**Not reliably reproducible, verified 2026-09-20.** A dry run of the same recipe/case pair, testing twice in direct succession, got a correct `COMPLETED`/`succeeded` response from `recipe.test.status` both times, no lie. The bad response above is real and happened once, but it looks timing-dependent rather than a thing you can reliably trigger on demand. Don't script a live demo around forcing it; if it happens, use it, and have a fallback line ready if it doesn't.

**The unguarded not-found warning doesn't visibly clear after you fix it.** It's a static per-index check, not branch-aware: after adding the if/else guard, `unguarded_fixed_index` kept firing on the same line, now inside the `if` branch, even though the fix is correct and `affects_readiness` stays `false` throughout. Don't stage a beat around watching the warning disappear from the panel. The correct framing is "the validator caught this before I ran it," not "the validator now says this is fine."

```
workspace_command("recipe.job.list", ["--recipe-id", "<id>", "--limit", "5"])
workspace_command("recipe.job.get",  ["--recipe-id", "<id>", "--job-id", "j-XXXX-XXXX-XX"])
```

The Dev API route `GET /recipes/{id}/jobs` returns richer failure detail: `error_type`, `error_id`, and the full message. Use it when diagnosing, and use `--status failed` to skip the noise.

## Skills that read Workato Data Tables

Three steps, no external connection, nothing to expire:

```
workato_skill.start_workflow(parameters_schema)
  → workato_db_table.get_records(table_id, filters=[{field_id, op_default, value_default}])
  → workato_skill.workflow_return_result(result={...})
```

Filters address columns by `field_id` (the column UUID), not by name. Read the table definition first to get them. Returned records key their fields by the same UUID with dashes replaced by underscores, which is easy to get wrong when mapping the result.

This is the lowest-risk way to give a skill live, mutable data. A row edited in the table shows up in the next tool call, which hardcoded payloads can never do.

## Picklist metadata can say a value is valid when the org rejects it

Verified 2026-09-20. `recipe.picklist.list` on `Refund.ProcessingMode` returned exactly two options, `Salesforce` and `External`. Setting it to `Salesforce` failed the actual write with `INVALID_OR_NULL_FOR_RESTRICTED_PICKLIST`. `External` worked.

The picklist call reports the connector's generic field metadata, not this org's live restricted-picklist configuration. Treat a `recipe.picklist.list` result as narrowing your options, not as proof a value will be accepted. When a write fails with a restricted-picklist error despite the value coming straight from the picklist call, the fix is to try another listed option, not to assume the field name or the picklist tool is broken.

## Testing a polling-trigger recipe does not force an immediate poll

Verified 2026-09-20, building a `salesforce.new_custom_object(sobject_name='Case', since_offset=0)`-triggered recipe. `recipe.test.start` on it goes `IN_PROGRESS` and stays there through the recipe's real poll interval (default a few minutes), even after a matching record already exists. Passing `trigger_event` has no effect here, same as the documented behavior for webhook recipes: only a genuinely new matching record, found on the recipe's own schedule, produces a job.

Creating a real case that should match (`create_case` tested live, `since_offset` set to "Recipe start") did not produce a job on `recipe.job.list` within roughly four minutes of waiting. Not confirmed whether this is the poll interval running its normal course or something specific to test mode; either way, don't script a live demo beat around "watch the polling recipe fire," the wait is long enough to kill momentum on stage. Verify separately, off-camera, with enough lead time for the real poll interval, or lower `___poll_interval` to its 5-minute minimum and start the recipe for real ahead of the segment rather than testing it live.

## A pushed skill is not started, and its MCP tool stays inactive until it is

Verified 2026-09-20. `workspace_push` on a skill-triggered recipe creates and attaches it, but does not start it. The recipe sits stopped, and its `SkillRecipeMCPTool` entry on any MCP server it's attached to reads `active=False`.

This is easy to miss because `recipe.test.start` still works and looks like proof the skill is live: it bypasses the MCP endpoint entirely and drives the recipe directly. A skill that tests clean can still be unreachable from a real MCP client.

Confirmed the mechanism, not just the symptom: running `recipe.start --recipe-id <id>` on one recipe flipped only that recipe's tool entry to `active=True` on the next `mcp_server` platform read, the other four (still stopped) stayed `active=False`. `active` is a direct mirror of the recipe's running state, nothing else. Start every recipe behind a Skill before treating "attached to the MCP server" as "usable from the MCP server":

```
workspace_command("recipe.start", ["--recipe-id", "<id>"])
```

Then re-read the MCP server and confirm every tool you expect to be callable shows `active=True`.

## A new MCP tool must not set name/title/description

Verified 2026-09-20, building the Customer Service MCP server for real. A `SkillRecipeMCPTool` for a skill already on the server can have `name`/`title`/`description` edited directly. A brand-new one cannot: passing them explicitly on an entry with `id=None` is rejected with "new MCP Server tool name, title and description are assigned by Workato."

For a new tool, set only `id=None` and `skill_handle=...`, and leave the rest at their empty defaults. Workato fills in `name`/`title`/`description` from the skill itself on push. Confirm with a platform `workspace_read` afterward, the derived values usually match the skill's own name and description.

## Checking connections before you build

`connection.list` requires a `--provider` and only returns **authorized** connections. A connection visible in the folder tree may exist but never have been authorized, and it will not appear. Query the providers you plan to use before designing around them:

```
workspace_command("connection.list", ["--provider", "salesforce", "slack", "netsuite"])
```

On the Dev API side, `GET /connections` returns everything with an `authorization_status`, and `connection_lost_at` tells you when a working connection broke.

## "Job succeeded" is not "the skill returned the right data"

Verified 2026-09-20, debugging `get_case_status`. A job with `status='succeeded'` and no `error` only means every step executed without throwing — it says nothing about whether `workflow_return_result` carried the data the caller actually needed. A skill that always takes its "not found" branch, or whose `result={...}` silently resolves to empty/wrong values, still reports `succeeded`.

Do not call a skill verified until you've read the actual `result` payload on the `workflow_return_result` line, for both branches, against input that is known to exist. A guessed test value (a hint-text example, a number copied from a sibling skill) is not evidence — it produced a legitimate `found: false` here that looked like a bug until it was traced to the input, not the recipe.

To find a real value to test with when you don't have one: temporarily broaden the query (drop the `WHERE` filter that depends on the untested parameter, keep `LIMIT 1`), push, run one test, read the real record back, then restore the original filter and push again. `workspace_push` refuses a running recipe (`Cannot edit recipe ... because it is running`) — `recipe.stop` first, edit, push, `recipe.start` again.

## `get_recipe_test_status` cannot be trusted — use the Dev API job endpoint instead

Extends the existing "Reading job logs" note above. In one full debugging session, `get_recipe_test_status` and `test_recipe`'s own returned status both reported `NO_TEST_RUN` on **every single poll**, dozens of times, immediately after `recipe.job.list` confirmed a job existed and had `completed`. This was not the occasional timing-dependent lie the earlier note describes — it never once resolved correctly that session.

Two more limits on the preview AIRO MCP's own job tools: `workspace_command("recipe.job.get", ...)` only returns a summary (`status`, `timings`, `steps` count) when given the `internal_id` from `recipe.job.list` — its own dynamic help says it wants the real `handle`, which `recipe.job.list` always prints as `<unavailable>` for these jobs. There is no way to get per-step input/output through the preview AIRO MCP alone.

The reliable path is the **Dev API**, specifically `workato-dev-api-preview` (not `workato-dev-api`, not `workato-airo-mcp-server`'s `job_get`/`job_list` — both of those reach a different, wrong workspace; confirm with `get_users_me` first, `team_name` must read the Customer Data & Personalization workspace):

```
get_recipes_jobs(recipe_id=<id>)                    # lists jobs, gives real handles
get_recipes_jobs_(recipe_id=<id>, id=<job handle>)   # full per-step input/output, every time
```

`get_recipes_jobs_`'s `lines[]` gives each step's `adapter_name`, `adapter_operation`, `input`, and `output` — including the exact `result` object a `workflow_return_result` step sent and what the platform recorded back. This is the only tool in this workspace that reliably shows you what a skill actually returned.

## `workato-dev-api-preview` can be configured correctly and still not connect

If `.mcp.json` has the right URL and token but the server never shows up as a usable tool prefix in a session, check `claude mcp get workato-dev-api-preview` before suspecting the token. A `Status: ✘ Rejected (see disabledMcpjsonServers in settings)` means a project-scoped MCP server was declined in a permission prompt at some point (possibly by a different session, possibly this one) — not a credential problem. Fix:

```bash
claude mcp reset-project-choices
```

then start a new `claude` session in the project directory and approve the prompt for both project `.mcp.json` servers. Also note `claude mcp list` only shows project-scoped servers when run **from inside the project directory** — run elsewhere, it silently shows only the global/user-level roster, which can look like the project server doesn't exist at all.

## Giving links to workspace assets

Use bare `preview.workato.com`, no `app.` subdomain (`https://preview.workato.com/recipes/<id>`, `.../recipes?fid=<folder_id>`, `.../recipes/<id>/job/<job_handle>`, etc.). Confirmed working 2026-09-20. An earlier version of this note claimed the opposite — that `app.` was required and dropping it broke the link — and that was wrong; corrected after Bennett explicitly asked for bare `preview.workato.com` and confirmed the resulting links worked.

## A skill result field set to `false` fails validation, even though `true` doesn't

Verified 2026-09-20, building `get_case_status` fresh in `Test Runs`. A `result_schema_json` field — tried as both `boolean` type and `string` type holding the literal `"true"`/`"false"` — reports `"Response/Found ... can't be blank"` on `test_recipe`, but only on the branch that sets it to the false-ish value. The identical field set to `true` in the sibling branch validates fine. This reproduced across four separate attempts: boolean `True`/`False`, string `"true"`/`"false"` (which the platform's own canonicalizer silently rewrites back into Python `True`/`False` in the pretty-printed source on every push, regardless of the field's declared type), and two different guard-condition rewrites. The value, not the condition, is the trigger.

Workaround: don't use `true`/`false`-shaped values for a result field at all. Rename them to something the canonicalizer won't pattern-match as a boolean, for example `"yes"`/`"no"`. That resolved it immediately with no other change. If a skill's result needs a real found/not-found flag, treat it as one of these string sentinels rather than a `boolean` field.

Separately: the `unguarded_fixed_index` static warning (see the entry above) also disappears and reappears depending on how the guard condition is written — `if search_sobjects_2['list_size']:` (a bare truthy check on the raw datapill) satisfies the analyzer, while `if f"{search_sobjects_2['list_size']}" != 0` (the platform's own auto-wrapped form, string-interpolated pill compared to an int) does not, and is also a real bug: a stringified pill is never `!= 0` as far as the comparison is concerned, so that guard is dead code, not just an unrecognized one. Prefer the bare form.

## A "not found" branch guarded by `list_size` truthiness never actually triggers — confirmed with a live test

Verified 2026-09-20, building the owner/comment fields onto `get_case_status`. This is a bigger version of the note above: it's not just cosmetic, it silently makes the "record not found" branch unreachable, and the recipe still validates clean and "succeeds" on every test.

`if search_sobjects_2['list_size']:` — written bare, exactly as the previous note recommends — gets pushed and pretty-printed back as `if f"{search_sobjects_2['list_size']}":`, every time, regardless of how many times it's rewritten to the bare form first. The platform is evaluating this as "is the pill present/non-blank," not "is it numerically nonzero," and a `list_size` of `0` is still present as the string `"0"`. Proven by testing with a real case number and a nonexistent one back to back: both produced `"condition": true` on the job's `if` line, and the nonexistent-case run then failed downstream (`'Object ID' must be present`) trying to read fields off an empty result, rather than falling into the else branch at all.

**Fix:** don't guard on a count or size pill. Guard on a field that is only present when there's an actual match, e.g. `if search_sobjects_2['Case'][0]['Id']:` instead of `if search_sobjects_2['list_size']:`. Indexing `[0]` into an empty array on this connector returns blank rather than raising, so the presence check works correctly, and it happens to be exactly the expression the `unguarded_fixed_index` warning already suggests writing — that warning was pointing at the real fix the whole time, not just flagging noise.

Same fix applies to a nested "no comments yet" branch guarded by `search_sobjects_soql_5['list_size']`: use `if search_sobjects_soql_5['CaseComment'][0]['CommentBody']:` instead.

**Do not trust a clean `test_recipe` result alone for any branch guarded this way.** Test both the branch that should trigger and the one that shouldn't, with real inputs for each, before calling a not-found/error path verified.

## Referencing multiple different indices of the same array pill in one formula silently collapses them all to `[0]`

Verified 2026-09-20, building `review_open_cases`. Writing `search_sobjects_soql_2['Case'][0]`, `[1]`, and `[2]` together — either as separate values in one `result={...}` dict, or as separate `elif` guard conditions checking `[1]['Id']` and `[2]['Id']` — validates clean, pushes clean, and tests clean. The actual job output showed the **same** first record three times: every `[1]` and `[2]` reference had silently become `[0]` in the platform's own canonicalized copy, confirmed by reading the recipe back after push. The `elif` conditions were affected the same way, so the branch meant to detect "exactly 2 open cases" was actually re-testing "is there at least 1," making the higher-count branches unreachable in a different way than the earlier list_size bug.

This is not the same bug as the `list_size` truthiness issue above — it reproduces even when each guard correctly checks a real presence field (`['Id']`), and it isn't about the guard at all, it's about the platform being unable to keep more than one distinct literal index of the same base array pill straight within a single step or a single set of sibling branches.

**Don't design a skill that needs to enumerate multiple items from one array pill by literal index (`[0]`, `[1]`, `[2]`, ...).** There is no fix found yet that keeps distinct indices distinct through a push. Workarounds that stayed within index `[0]` only, verified to work correctly:
- Report a count (`list_size`) plus a single most-relevant item (e.g. sorted by priority/date, take `[0]`) rather than a per-item breakdown.
- A real per-item list would need the `workato_variable` connector's `declare_list`/`insert_to_list`/`foreach` machinery (see `workato-guides/patterns/conditions-and-loops.md` and `workato-guides/connectors/variables.md`) rather than manual indexing — not verified in this workspace yet, budget permitting try that path next time this limitation blocks a real requirement.

**A `ruby(...)` formula argument containing Ruby string interpolation (`#{...}`) failed to parse** as a `workflow_return_result` field value in this same build, reporting `FormulaParseError` with the argument mysteriously prefixed `=` and suffixed `# INVALID RUBY FORMULA`. Not root-caused; a `bindings={...}` bare bindings dict fixed the earlier "must be a dictionary" complaint but the interpolation body itself never got past parsing. Avoid `ruby()` with `#{}` interpolation in a skill result field until this is understood; plain Python-style `f"{pill}"` string building works fine and was used instead everywhere in this build.

## The documented `Test Runs` and `Customer Service MCP` subfolder IDs can go stale

Verified 2026-09-20. `folder.list --parent-id 583806` returned zero items, and both `workspace_read` and the Dev API `get_folders_` 404'd on `583807` (`Test Runs`) and `583808` (`Customer Service MCP`), the IDs recorded throughout this repo's docs. `project.list` still saw the parent project fine, and `get_projects_project_grants` showed the pushing identity as Project admin, so it wasn't a grants problem this time, the subfolders themselves no longer exist on the platform. Recreated `Test Runs` via the Dev API (`POST /folders`, `parent_id=583806`) at a new ID, `583843`. If a push fails with `Folder with id 'NNN' was not found`, check both the grants gotcha above and this one — confirm the folder is actually still there (`get_folders_` on the Dev API is the fastest check) before assuming either cause.
