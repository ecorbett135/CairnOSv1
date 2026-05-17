# Security Policy

## Supported Versions

CairnOSv1 is currently public alpha software. Security review and support focus
on the active `alpha` and `dev` branches.

| Version / Branch | Supported |
| --- | --- |
| `alpha` | Yes |
| `dev` | Yes |
| `master` | Best effort |
| Older feature branches | No |

## Reporting A Vulnerability

Do not open a public GitHub issue for sensitive security reports.

Please report security concerns through GitHub private vulnerability reporting
or a private maintainer channel when available. If neither is available, ask
the maintainer for a private contact path without posting exploit details in a
public issue. Include:

- a short description of the issue
- affected files, branches, or deployed app behavior
- steps to reproduce, if safe to share
- impact or risk
- any suggested fix

If the issue involves the hosted Streamlit alpha, include the app URL and the
approximate time observed.

## What Counts As Security-Sensitive

Examples include:

- exposed secrets, tokens, private form-management links, or credentials
- dependency vulnerabilities that affect the hosted app or local users
- unsafe file handling or path traversal
- cross-site scripting or injection risk in user-facing output
- behavior that could expose private tester data

Trail-data accuracy, route realism, and field safety concerns are important, but
they should normally be reported as trail/data issues or alpha feedback unless
they also expose a software security risk.

## Dependency And Hygiene Expectations

- Do not commit secrets, private Streamlit settings, raw credentials, or private
  tester data.
- Keep generated outputs and local calibration exports out of git unless they
  are deliberate, provenance-reviewed artifacts.
- Prefer minimal runtime dependencies for the hosted Streamlit app.
- Run tests before merging changes that affect planning, exports, or user input.
- Review dependency updates for license and security implications.
