# Desktop SSH worker acceptance

Bounded slice: add an ordinary OpenSSH `desktop` profile usable from Termux after the deterministic Adam terminal-shell worker is integrated.

Acceptance:
- installer exposes `adam-ssh-profile`
- generated config supports `ssh desktop`
- no password or private-key material is stored by the tool
- alias/host/user/identity config-injection attempts are rejected
- reinstall does not duplicate the Include directive
- existing Adam terminal-shell behavior remains untouched
- repository gates pass
- Venice external review of the exact current-base -> head diff returns PASS before merge
