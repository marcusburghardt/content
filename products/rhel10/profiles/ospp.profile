---
documentation_complete: true

metadata:
    version: 4.3
    SMEs:
        - ggbecker
        - matusmarhefka

reference: https://www.niap-ccevs.org/Profile/Info.cfm?PPID=469&id=469

title: 'DRAFT - Protection Profile for General Purpose Operating Systems'

description: |-
    This is draft profile is based on the Red Hat Enterprise Linux 9 Common Criteria Guidance as
    guidance for Red Hat Enterprise Linux 10 was not available at the time of release.

    Where appropriate, CNSSI 1253 or DoD-specific values are used for
    configuration, based on Configuration Annex to the OSPP.

selections:
    - ospp:all
    - var_authselect_profile=local

    - '!package_screen_installed'
    - '!package_dnf-plugin-subscription-manager_installed'
    - '!package_scap-security-guide_installed'
    # Currently not working RHEL 10, changes are being made to FIPS mode. Investigation is recommended.
    - '!enable_dracut_fips_module'
