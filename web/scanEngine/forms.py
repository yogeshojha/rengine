from django import forms
from django_ace import AceWidget
from reNgine.validators import validate_short_name
from scanEngine.models import *


class AddEngineForm(forms.ModelForm):
    class Meta:
        model = EngineType
        fields = '__all__'
    engine_name = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "id": "scan_engine_name",
                "placeholder": "Engine Name"}))
    yaml_configuration = forms.CharField(widget=AceWidget(
        mode="yaml",
        theme="tomorrow_night_eighties",
        width="100%",
        height="450px",
        tabsize=2,
        fontsize='17px',
        showinvisibles=True,
        attrs={"id": "editor"}))


class UpdateEngineForm(forms.ModelForm):
    class Meta:
        model = EngineType
        fields = '__all__'
    engine_name = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "id": "scan_engine_name",
                "placeholder": "Custom Engine"}))
    yaml_configuration = forms.CharField(widget=AceWidget(
        mode="yaml",
        theme="tomorrow_night_eighties",
        width="100%",
        height="450px",
        tabsize=2,
        fontsize='17px',
        showinvisibles=True,
        attrs={"id": "editor"}))

class AddWordlistForm(forms.Form):
    name = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={'class': 'form-control form-control-lg',
                   'id': 'name',
                   'placeholder': 'my awesome wordlist', }))
    short_name = forms.CharField(
        required=True,
        validators=[validate_short_name],
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-lg',
                'id': 'short_name',
                'placeholder': 'my_awesome_wordlist', }))
    upload_file = forms.FileField(
        required=True,
        widget=forms.FileInput(
            attrs={'class': 'form-control',
                   'id': 'txtFile',
                   'multiple': '',
                   'accept': '.txt', }))


class ConfigurationForm(forms.ModelForm):
    class Meta:
        model = Configuration
        fields = '__all__'
    name = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={'class': 'form-control form-control-lg',
                   'id': 'name',
                   'placeholder': 'Configuration Name', }))
    short_name = forms.CharField(
        required=True,
        validators=[validate_short_name],
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-lg',
                'id': 'short_name',
                'placeholder': 'my_awesome_configuration', }))
    content = forms.CharField(widget=AceWidget(
        mode="text",
        theme="monokai",
        width="100%",
        height="450px",
        tabsize=4,
        fontsize=13,
        toolbar=True,))

    def set_value(self, configuration):
        self.initial['name'] = configuration.name
        self.initial['short_name'] = configuration.short_name
        self.initial['content'] = configuration.content


class InterestingLookupForm(forms.ModelForm):
    class Meta:
        model = InterestingLookupModel
        fields = '__all__'
    keywords = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "id": "keywords",
                "placeholder": "Interesting Keywords",
            }))

    custom_type = forms.BooleanField(
        required=False,
        widget=forms.HiddenInput(
            attrs={
                "value": 'true'
                }))

    title_lookup = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "title_lookup"
            }))

    url_lookup = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "url_lookup"
            }))

    condition_200_http_lookup = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "condition_200_http_lookup"
            }))

    def set_value(self, key):
        print(key.url_lookup)
        self.initial['keywords'] = key.keywords
        self.initial['title_lookup'] = key.title_lookup
        self.initial['url_lookup'] = key.url_lookup
        self.initial['condition_200_http_lookup'] = key.condition_200_http_lookup

    def initial_checkbox(self):
        self.initial['title_lookup'] = True
        self.initial['url_lookup'] = True
        self.initial['condition_200_http_lookup'] = False


class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = '__all__'

    send_to_slack = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "slack_checkbox",
            }))

    slack_hook_url = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control h-100",
                "id": "slack_hook_url",
                "placeholder": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
            },
            render_value=True
        ))

    send_to_lark = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "lark_checkbox",
            }))

    lark_hook_url = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control h-100",
                "id": "lark_hook_url",
                "placeholder": "https://open.larksuite.com/open-apis/bot/v2/hook/XXXXXXXXXXXXXXXXXXXXXXXX",
            },
            render_value=True
        ))

    send_to_discord = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "discord_checkbox",
            }))

    discord_hook_url = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control h-100",
                "id": "discord_hook_url",
                "placeholder": "https://discord.com/api/webhooks/000000000000000000/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            },
            render_value=True
        ))

    send_to_telegram = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "telegram_checkbox",
            }))

    telegram_bot_token = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control h-100",
                "id": "telegram_bot_token",
                "placeholder": "Bot Token",
            },
            render_value=True
        ))

    telegram_bot_chat_id = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control h-100",
                "id": "telegram_bot_chat_id",
                "placeholder": "Bot Chat ID",
            },
            render_value=True
        ))

    send_scan_status_notif = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "send_scan_status_notif",
            }))

    send_interesting_notif = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "send_interesting_notif",
            }))


    send_vuln_notif = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "send_vuln_notif",
            }))


    send_subdomain_changes_notif = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "send_subdomain_changes_notif",
            }))


    send_scan_output_file = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "send_scan_output_file",
            }))

    send_scan_tracebacks = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "send_scan_tracebacks",
            }))


    def set_value(self, key):
        self.initial['send_to_slack'] = key.send_to_slack
        self.initial['send_to_lark'] = key.send_to_lark
        self.initial['send_to_discord'] = key.send_to_discord
        self.initial['send_to_telegram'] = key.send_to_telegram

        self.initial['slack_hook_url'] = key.slack_hook_url
        self.initial['lark_hook_url'] = key.lark_hook_url
        self.initial['discord_hook_url'] = key.discord_hook_url
        self.initial['telegram_bot_token'] = key.telegram_bot_token
        self.initial['telegram_bot_chat_id'] = key.telegram_bot_chat_id

        self.initial['send_scan_status_notif'] = key.send_scan_status_notif
        self.initial['send_interesting_notif'] = key.send_interesting_notif
        self.initial['send_vuln_notif'] = key.send_vuln_notif
        self.initial['send_subdomain_changes_notif'] = key.send_subdomain_changes_notif

        self.initial['send_scan_output_file'] = key.send_scan_output_file
        self.initial['send_scan_tracebacks'] = key.send_scan_tracebacks

        if not key.send_to_slack:
            self.fields['slack_hook_url'].widget.attrs['readonly'] = True
        if not key.send_to_lark:
            self.fields['lark_hook_url'].widget.attrs['readonly'] = True
        if not key.send_to_discord:
            self.fields['discord_hook_url'].widget.attrs['readonly'] = True
        if not key.send_to_telegram:
            self.fields['telegram_bot_token'].widget.attrs['readonly'] = True
            self.fields['telegram_bot_chat_id'].widget.attrs['readonly'] = True


    def set_initial(self):
        self.initial['send_to_slack'] = False
        self.initial['send_to_lark'] = False
        self.initial['send_to_discord'] = False
        self.initial['send_to_telegram'] = False

        self.fields['slack_hook_url'].widget.attrs['readonly'] = True
        self.fields['lark_hook_url'].widget.attrs['readonly'] = True
        self.fields['discord_hook_url'].widget.attrs['readonly'] = True
        self.fields['telegram_bot_token'].widget.attrs['readonly'] = True
        self.fields['telegram_bot_chat_id'].widget.attrs['readonly'] = True

        self.initial['send_scan_status_notif'] = True
        self.initial['send_interesting_notif'] = True
        self.initial['send_vuln_notif'] = True
        self.initial['send_subdomain_changes_notif'] = True

        self.initial['send_scan_output_file'] = True
        self.initial['send_scan_tracebacks'] = True


class ProxyForm(forms.ModelForm):
    class Meta:
        model = Proxy
        fields = '__all__'

    use_proxy = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "use_proxy",
            }))

    proxies = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "id": "proxies",
                "rows": "10",
                "spellcheck": "false",
                "placeholder": "http://username:password@proxyip.com:port",
            }))

    def set_value(self, key):
        self.initial['use_proxy'] = key.use_proxy
        self.initial['proxies'] = key.proxies

        if not key.use_proxy:
            self.fields['proxies'].widget.attrs['readonly'] = True

    def set_initial(self):
        self.initial['use_proxy'] = False
        self.fields['proxies'].widget.attrs['readonly'] = True


class HackeroneForm(forms.ModelForm):
    class Meta:
        model = Hackerone
        fields = '__all__'

    send_report = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "send_report",
            }))

    send_critical = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "send_critical",
            }))

    send_high = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "send_high",
            }))

    send_medium = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "send_medium",
            }))

    report_template = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "id": "vulnerability-report-template"
            }))

    def set_value(self, key):
        self.initial['username'] = key.username
        self.initial['api_key'] = key.api_key

        self.initial['send_report'] = key.send_report
        self.initial['send_critical'] = key.send_critical
        self.initial['send_high'] = key.send_high
        self.initial['send_medium'] = key.send_medium

        self.initial['report_template'] = key.report_template

    def set_initial(self):
        self.initial['send_report'] = False
        self.initial['send_critical'] = True
        self.initial['send_high'] = True
        self.initial['send_medium'] = False

        self.initial['report_template'] = '''Hi Team, while testing, a {vulnerability_severity} severity vulnerability has been discovered in {vulnerable_url} and below is the findings.

# Vulnerability
{vulnerability_name}

## Issue Description
{vulnerability_description}

## Vulnerable URL
- {vulnerable_url}

## Extracted Results/Findings
{vulnerability_extracted_results}

## References
- {vulnerability_reference}

Thank you'''


class ReportForm(forms.ModelForm):
    class Meta:
        model = VulnerabilityReportSetting
        fields = '__all__'

    company_name = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "id": "company_name",
                "placeholder": "Company Name",
            }))

    company_address = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "id": "company_address",
                "placeholder": "Company Address",
            }))

    company_website = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "id": "company_website",
                "placeholder": "Company Website https://company.com",
            }))

    company_email = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "id": "company_email",
                "placeholder": "email@yourcompany.com",
            }))

    show_footer = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "show_footer",
            }))

    footer_text = forms.CharField(
        required=False,
        widget=forms.TextInput(
        attrs={
            "class": "form-control form-control-lg",
            "id": "footer_text",
            "aria-label": "switch",
            "placeholder": "Footer Text © Your Company",
        }))

    show_rengine_banner = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "show_rengine_banner",
            }))

    show_executive_summary = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "show_executive_summary",
            }))

    executive_summary_description = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "id": "executive_summary_description"
            }))

    primary_color = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "id": "primary_color",
                "hidden": "true"
            }))

    secondary_color = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "id": "secondary_color",
                "hidden": "true"
            }))

    def set_value(self, key):
        self.initial['company_name'] = key.company_name
        self.initial['company_address'] = key.company_address
        self.initial['company_website'] = key.company_website
        self.initial['company_email'] = key.company_email
        self.initial['show_rengine_banner'] = key.show_rengine_banner
        self.initial['show_executive_summary'] = key.show_executive_summary
        self.initial['executive_summary_description'] = key.executive_summary_description
        self.initial['show_footer'] = key.show_footer
        self.initial['footer_text'] = key.footer_text
        self.initial['primary_color'] = key.primary_color
        self.initial['secondary_color'] = key.secondary_color

    def set_initial(self):
        self.initial['show_rengine_banner'] = True
        self.initial['show_footer'] = False
        self.initial['show_executive_summary'] = False
        self.initial['primary_color'] = '#FFB74D'
        self.initial['secondary_color'] = '#212121'
        self.initial['executive_summary_description'] = '''On **{scan_date}**, **{target_name}** engaged **{company_name}** to perform a security audit on their Web application.

**{company_name}** performed both Security Audit and Reconnaissance using automated tool reNgine. https://github.com/yogeshojha/rengine .

## Observations

During the course of this engagement **{company_name}** was able to discover **{subdomain_count}** Subdomains and  **{vulnerability_count}** Vulnerabilities, including informational vulnerabilities and these could pose a significant risk to the security of the application.

The breakdown of the Vulnerabilities Identified in **{target_name}** by severity are as follows:

* Critical : {critical_count}
* High : {high_count}
* Medium : {medium_count}
* Low : {low_count}
* Info : {info_count}
* Unknown : {unknown_count}

**{company_name}** recommends that these issues be addressed in timely manner.

'''


class ExternalToolForm(forms.ModelForm):
    class Meta:
        model = InstalledExternalTool
        fields = '__all__'

    name = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "tool_name",
                "placeholder": "My Awesome Tool"}))

    github_url = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "github_url",
                "placeholder": "https://github.com/"}))

    license_url = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "license_url",
                "placeholder": "https://github.com/user/tool/blob/master/LICENSE.md"}))

    logo_url = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "logo_url",
                "placeholder": "http://example.com/logo.png"}))

    description = forms.CharField(
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "id": "tool_description",
                "placeholder": "Explain what this tool is used for.",
                "rows": 2
            }
        ))

    install_command = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "install_command",
                "placeholder": "Tool Installation Command"}))

    update_command = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "update_command",
                "placeholder": "Tool Update Command"}))

    version_match_regex = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "version_match_regex",
                "value": "[vV]*(\d+\.)?(\d+\.)?(\*|\d+)"
                }))

    version_lookup_command = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "version_lookup_command"}))

    is_subdomain_gathering = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            "id": "is_subdomain_gathering",
            "class": "switch",
        }))

    subdomain_gathering_command = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "subdomain_gathering_command",
                "placeholder": "Subdomain Gathering Command",
                "value": "tool_name -d {TARGET} -o {OUTPUT}"
                }))

    def set_value(self, key):
        self.initial['name'] = key.name
        self.initial['github_url'] = key.github_url
        self.initial['license_url'] = key.license_url
        self.initial['logo_url'] = key.logo_url
        self.initial['description'] = key.description
        self.initial['install_command'] = key.install_command
        self.initial['update_command'] = key.update_command
        self.initial['version_match_regex'] = key.version_match_regex
        self.initial['version_lookup_command'] = key.version_lookup_command
        self.initial['subdomain_gathering_command'] = key.subdomain_gathering_command
