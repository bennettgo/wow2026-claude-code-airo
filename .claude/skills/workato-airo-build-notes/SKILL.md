---
name: workato-airo-build-notes
description: Hard-won gotchas for building Workato assets through the AIRO MCP and Dev API MCP, covering skill creation, MCP server attachment, token minting, testing, job logs, and data-table-backed skills. Use whenever creating or debugging a Workato Skill, MCP server, Genie, or recipe through an MCP tool, or when an AIRO call fails in a way the error message does not explain.
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

A recipe using the `workato_skill` trigger needs an explicit `"config": "[]"` field at creation. Without it the recipe is created but cannot be started, and the error is `missing adapter configuration: workato_skill`, which does not point at the missing field.

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

- **`get_recipe_test_status` lies.** It reported `NO_TEST_RUN` while the test job had already run and succeeded. Do not script it. Go to the job list instead.
- `recipe.job.list` prints `handle=<unavailable>`, but its `internal_id` works as the `--job-id` argument to `recipe.job.get`.

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

## Checking connections before you build

`connection.list` requires a `--provider` and only returns **authorized** connections. A connection visible in the folder tree may exist but never have been authorized, and it will not appear. Query the providers you plan to use before designing around them:

```
workspace_command("connection.list", ["--provider", "salesforce", "slack", "netsuite"])
```

On the Dev API side, `GET /connections` returns everything with an `authorization_status`, and `connection_lost_at` tells you when a working connection broke.
