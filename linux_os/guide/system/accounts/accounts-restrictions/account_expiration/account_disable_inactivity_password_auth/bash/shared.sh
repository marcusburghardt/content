# platform = multi_platform_ol

PAM_FILE_PATH="/etc/pam.d/password-auth"
if [ -f /usr/bin/authselect ]; then
    {{{ bash_check_authselect_integrity() | indent(4) }}}
    {{{ bash_ensure_authselect_custom_profile() | indent(4) }}}
    PAM_FILE_NAME=$(basename "$PAM_FILE_PATH")
    PAM_FILE_PATH="/etc/authselect/$CURRENT_PROFILE/$PAM_FILE_NAME"
    authselect apply-changes -b --backup=before-hardening-pam_lastlog.so-inactive.backup
fi
{{{ bash_ensure_pam_module_option("$PAM_FILE_PATH",
                                  'auth',
                                  'required',
                                  'pam_lastlog.so',
                                  'inactive', '35') }}}
{{{ bash_ensure_pam_module_line("$PAM_FILE_PATH",
                                'auth',
                                'sufficient', 
                                'pam_unix.so',
                                '^\s*auth.*required.*pam_lastlog\.so.*') }}}
# Ensure pam_unix.so is configured after pam_lastlog.so
if ! grep -Pz \
    "auth\s*required\s*pam_lastlog\.so[^#]*inactive=35[\s\S]*\n\s*auth\s*sufficient\s*pam_unix\.so"\
    "$PAM_FILE_PATH"  ; then
    readarray -t pam_lastlog_lines <<< "$(grep -oP '^\s*auth.*pam_lastlog\.so[^#]*inactive=35.*' $PAM_FILE_PATH)"
    sed -i "/^\s*auth.*pam_lastlog\.so[^#]*inactive=35.*/d" "$PAM_FILE_PATH"
    for line in "${pam_lastlog_lines[@]}"; do
        sed -i "/^\s*auth.*pam_unix\.so.*/i$line" "$PAM_FILE_PATH"
    done
fi
if [ -f /usr/bin/authselect ]; then
    authselect apply-changes -b --backup=after-hardening-pam_lastlog.so-inactive.backup
fi
