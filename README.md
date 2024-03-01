# TermHub shadow fork
## Purpose
For running 'premium actions' (large runners) not able to currently run currently on JHU enterprise account.

## Additional info
The branch 'shadow-develop' is simply a copy of TermHub's develop branch, with 1+ additional commits on top of it for 
deactivation / activation of relevant GitHub action, documentation, and anything else necessary for the purposes of 
utilizing large runners.

## Changes
- Update: Deactivated all cronjobs on all actions other than vocab/counts.
- Update: Activated cronjobs for GitHub actions for vocab/counts
- Update: README.md: Documentation about the shadow fork specifically.

---

## Maintaining
Periodically do `git checkout shadow-develop; git rebase develop; git push -uf shadow shadow-develop`
