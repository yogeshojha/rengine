import io
import re
import os
import subprocess
import glob
import shutil

from django.shortcuts import render, get_object_or_404
from scanEngine.models import *
from scanEngine.forms import *
from scanEngine.forms import ConfigurationForm
from django.contrib import messages
from django import http
from django.urls import reverse
from django.conf import settings
from django.core.files.storage import default_storage

from reNgine.common_func import *
from reNgine.tasks import run_system_commands


def index(request):
    engine_type = EngineType.objects.all().order_by('id')
    context = {
        'engine_ul_show': 'show',
        'engine_li': 'active',
        'scan_engine_nav_active': 'active',
        'engine_type': engine_type, }
    return render(request, 'scanEngine/index.html', context)


def add_engine(request):
    form = AddEngineForm()
    if request.method == "POST":
        form = AddEngineForm(request.POST)
        if form.is_valid():
            form.save()
            messages.add_message(
                request,
                messages.INFO,
                'Scan Engine Added successfully')
            return http.HttpResponseRedirect(reverse('scan_engine_index'))
    context = {
            'scan_engine_nav_active':
            'active', 'form': form}
    return render(request, 'scanEngine/add_engine.html', context)


def delete_engine(request, id):
    obj = get_object_or_404(EngineType, id=id)
    if request.method == "POST":
        obj.delete()
        responseData = {'status': 'true'}
        messages.add_message(
            request,
            messages.INFO,
            'Engine successfully deleted!')
    else:
        responseData = {'status': 'false'}
        messages.add_message(
            request,
            messages.ERROR,
            'Oops! Engine could not be deleted!')
    return http.JsonResponse(responseData)


def update_engine(request, id):
    engine = get_object_or_404(EngineType, id=id)
    form = UpdateEngineForm()
    if request.method == "POST":
        form = UpdateEngineForm(request.POST, instance=engine)
        if form.is_valid():
            form.save()
            messages.add_message(
                request,
                messages.INFO,
                'Engine edited successfully')
            return http.HttpResponseRedirect(reverse('scan_engine_index'))
    else:
        form.set_value(engine)
    context = {
            'scan_engine_nav_active':
            'active', 'form': form}
    return render(request, 'scanEngine/update_engine.html', context)


def wordlist_list(request):
    wordlists = Wordlist.objects.all().order_by('id')
    context = {
            'scan_engine_nav_active': 'active',
            'wordlist_li': 'active',
            'wordlists': wordlists}
    return render(request, 'scanEngine/wordlist/index.html', context)


def add_wordlist(request):
    context = {'scan_engine_nav_active': 'active', 'wordlist_li': 'active'}
    form = AddWordlistForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if form.is_valid() and 'upload_file' in request.FILES:
            txt_file = request.FILES['upload_file']
            if txt_file.content_type == 'text/plain':
                wordlist_content = txt_file.read().decode('UTF-8', "ignore")
                wordlist_file = open(
                    '/usr/src/' +
                    'wordlist/' +
                    form.cleaned_data['short_name'] + '.txt',
                    'w')
                wordlist_file.write(wordlist_content)
                Wordlist.objects.create(
                    name=form.cleaned_data['name'],
                    short_name=form.cleaned_data['short_name'],
                    count=wordlist_content.count('\n'))
                messages.add_message(
                    request,
                    messages.INFO,
                    'Wordlist ' + form.cleaned_data['name'] +
                    ' added successfully')
                return http.HttpResponseRedirect(reverse('wordlist_list'))
    context['form'] = form
    return render(request, 'scanEngine/wordlist/add.html', context)


def delete_wordlist(request, id):
    obj = get_object_or_404(Wordlist, id=id)
    if request.method == "POST":
        obj.delete()
        try:
            os.remove(
            '/usr/src/' +
            'wordlist/' +
            obj.short_name +
            '.txt')
            responseData = {'status': True}
        except Exception as e:
            responseData = {'status': False}
        messages.add_message(
            request,
            messages.INFO,
            'Wordlist successfully deleted!')
    else:
        responseData = {'status': 'false'}
        messages.add_message(
            request,
            messages.ERROR,
            'Oops! Wordlist could not be deleted!')
    return http.JsonResponse(responseData)


def interesting_lookup(request):
    lookup_keywords = None
    context = {}
    context['scan_engine_nav_active'] = 'active'
    context['interesting_lookup_li'] = 'active'
    context['engine_ul_show'] = 'show'
    form = InterestingLookupForm()
    if InterestingLookupModel.objects.filter(custom_type=True).exists():
        lookup_keywords = InterestingLookupModel.objects.filter(custom_type=True).order_by('-id')[0]
    else:
        form.initial_checkbox()
    if request.method == "POST":
        if lookup_keywords:
            form = InterestingLookupForm(request.POST, instance=lookup_keywords)
        else:
            form = InterestingLookupForm(request.POST or None)
        print(form.errors)
        if form.is_valid():
            print(form.cleaned_data)
            form.save()
            messages.add_message(
                request,
                messages.INFO,
                'Lookup Keywords updated successfully')
            return http.HttpResponseRedirect(reverse('interesting_lookup'))

    if lookup_keywords:
        form.set_value(lookup_keywords)
        context['interesting_lookup_found'] = True
    context['form'] = form
    context['default_lookup'] = InterestingLookupModel.objects.filter(id=1)
    return render(request, 'scanEngine/lookup.html', context)

def tool_specific_settings(request):
    context = {}
    # check for incoming form requests
    if request.method == "POST":

        print(request.FILES)
        if 'gfFileUpload' in request.FILES:
            gf_file = request.FILES['gfFileUpload']
            file_extension = gf_file.name.split('.')[len(gf_file.name.split('.'))-1]
            if file_extension != 'json':
                messages.add_message(request, messages.ERROR, 'Invalid GF Pattern, upload only *.json extension')
            else:
                # remove special chars from filename, that could possibly do directory traversal or XSS
                filename = re.sub(r'[\\/*?:"<>|]',"", gf_file.name)
                file_path = '/root/.gf/' + filename
                file = open(file_path, "w")
                file.write(gf_file.read().decode("utf-8"))
                file.close()
                messages.add_message(request, messages.INFO, 'Pattern {} successfully uploaded'.format(gf_file.name[:4]))
            return http.HttpResponseRedirect(reverse('tool_settings'))

        elif 'nucleiFileUpload' in request.FILES:
            nuclei_file = request.FILES['nucleiFileUpload']
            file_extension = nuclei_file.name.split('.')[len(nuclei_file.name.split('.'))-1]
            if file_extension != 'yaml':
                messages.add_message(request, messages.ERROR, 'Invalid Nuclei Pattern, upload only *.yaml extension')
            else:
                filename = re.sub(r'[\\/*?:"<>|]',"", nuclei_file.name)
                file_path = '/root/nuclei-templates/' + filename
                file = open(file_path, "w")
                file.write(nuclei_file.read().decode("utf-8"))
                file.close()
                messages.add_message(request, messages.INFO, 'Nuclei Pattern {} successfully uploaded'.format(nuclei_file.name[:-5]))
            return http.HttpResponseRedirect(reverse('tool_settings'))

        elif 'nuclei_config_text_area' in request.POST:
            with open('/root/.config/nuclei/config.yaml', "w") as fhandle:
                fhandle.write(request.POST.get('nuclei_config_text_area'))
            messages.add_message(request, messages.INFO, 'Nuclei config updated!')
            return http.HttpResponseRedirect(reverse('tool_settings'))

        elif 'subfinder_config_text_area' in request.POST:
            with open('/root/.config/subfinder/config.yaml', "w") as fhandle:
                fhandle.write(request.POST.get('subfinder_config_text_area'))
            messages.add_message(request, messages.INFO, 'Subfinder config updated!')
            return http.HttpResponseRedirect(reverse('tool_settings'))

        elif 'naabu_config_text_area' in request.POST:
            with open('/root/.config/naabu/config.yaml', "w") as fhandle:
                fhandle.write(request.POST.get('naabu_config_text_area'))
            messages.add_message(request, messages.INFO, 'Naabu config updated!')
            return http.HttpResponseRedirect(reverse('tool_settings'))

        elif 'amass_config_text_area' in request.POST:
            with open('/root/.config/amass.ini', "w") as fhandle:
                fhandle.write(request.POST.get('amass_config_text_area'))
            messages.add_message(request, messages.INFO, 'Amass config updated!')
            return http.HttpResponseRedirect(reverse('tool_settings'))
        
        elif 'theharvester_config_text_area' in request.POST:
            with open('/usr/src/github/theHarvester/api-keys.yaml', "w") as fhandle:
                fhandle.write(request.POST.get('theharvester_config_text_area'))
            messages.add_message(request, messages.INFO, 'theHarvester config updated!')
            return http.HttpResponseRedirect(reverse('tool_settings'))

    context['settings_nav_active'] = 'active'
    context['tool_settings_li'] = 'active'
    context['settings_ul_show'] = 'show'
    gf_list = (subprocess.check_output(['gf', '-list'])).decode("utf-8")
    nuclei_custom_pattern = [f for f in glob.glob("/root/nuclei-templates/*.yaml")]
    context['nuclei_templates'] = nuclei_custom_pattern
    context['gf_patterns'] = sorted(gf_list.split('\n'))
    return render(request, 'scanEngine/settings/tool.html', context)

def rengine_settings(request):
    context = {}

    total, used, _ = shutil.disk_usage("/")
    total = total // (2**30)
    used = used // (2**30)
    context['total'] = total
    context['used'] = used
    context['free'] = total-used
    context['consumed_percent'] = int(100 * float(used)/float(total))

    context['settings_nav_active'] = 'active'
    context['rengine_settings_li'] = 'active'
    context['settings_ul_show'] = 'show'

    return render(request, 'scanEngine/settings/rengine.html', context)

def notification_settings(request):
    context = {}
    form = NotificationForm()
    notification = None
    if Notification.objects.all().exists():
        notification = Notification.objects.all()[0]
        form.set_value(notification)
    else:
        form.set_initial()

    if request.method == "POST":
        if notification:
            form = NotificationForm(request.POST, instance=notification)
        else:
            form = NotificationForm(request.POST or None)

        if form.is_valid():
            form.save()
            send_slack_message('*reNgine*\nCongratulations! your notification services are working.')
            send_telegram_message('*reNgine*\nCongratulations! your notification services are working.')
            send_discord_message('**reNgine**\nCongratulations! your notification services are working.')
            messages.add_message(
                request,
                messages.INFO,
                'Notification Settings updated successfully and test message was sent.')
            return http.HttpResponseRedirect(reverse('notification_settings'))

    context['settings_nav_active'] = 'active'
    context['notification_settings_li'] = 'active'
    context['settings_ul_show'] = 'show'
    context['form'] = form

    return render(request, 'scanEngine/settings/notification.html', context)

def proxy_settings(request):
    context = {}
    form = ProxyForm()
    context['form'] = form

    proxy = None
    if Proxy.objects.all().exists():
        proxy = Proxy.objects.all()[0]
        form.set_value(proxy)
    else:
        form.set_initial()

    if request.method == "POST":
        if proxy:
            form = ProxyForm(request.POST, instance=proxy)
        else:
            form = ProxyForm(request.POST or None)

        if form.is_valid():
            form.save()
            messages.add_message(
                request,
                messages.INFO,
                'Proxies updated.')
            return http.HttpResponseRedirect(reverse('proxy_settings'))


    context['settings_nav_active'] = 'active'
    context['proxy_settings_li'] = 'active'
    context['settings_ul_show'] = 'show'

    return render(request, 'scanEngine/settings/proxy.html', context)


def test_hackerone(request):
    context = {}
    if request.method == "POST":
        headers = {
            'Accept': 'application/json'
        }
        body = json.loads(request.body)
        r = requests.get(
            'https://api.hackerone.com/v1/hackers/payments/balance',
            auth=(body['username'], body['api_key']),
            headers = headers
        )
        if r.status_code == 200:
            return http.JsonResponse({"status": 200})

    return http.JsonResponse({"status": 401})


def hackerone_settings(request):
    context = {}
    form = HackeroneForm()
    context['form'] = form

    hackerone = None
    if Hackerone.objects.all().exists():
        hackerone = Hackerone.objects.all()[0]
        form.set_value(hackerone)
    else:
        form.set_initial()

    if request.method == "POST":
        if hackerone:
            form = HackeroneForm(request.POST, instance=hackerone)
        else:
            form = HackeroneForm(request.POST or None)

        if form.is_valid():
            form.save()
            messages.add_message(
                request,
                messages.INFO,
                'Hackerone Settings updated.')
            return http.HttpResponseRedirect(reverse('hackerone_settings'))


    context['settings_nav_active'] = 'active'
    context['hackerone_settings_li'] = 'active'
    context['settings_ul_show'] = 'show'

    return render(request, 'scanEngine/settings/hackerone.html', context)


def report_settings(request):
    context = {}
    form = ReportForm()
    context['form'] = form

    primary_color = '#FFB74D'
    secondary_color = '#212121'

    report = None
    if VulnerabilityReportSetting.objects.all().exists():
        report = VulnerabilityReportSetting.objects.all()[0]
        primary_color = report.primary_color
        secondary_color = report.secondary_color
        form.set_value(report)
    else:
        form.set_initial()

    if request.method == "POST":
        if report:
            form = ReportForm(request.POST, instance=report)
        else:
            form = ReportForm(request.POST or None)

        if form.is_valid():
            form.save()
            messages.add_message(
                request,
                messages.INFO,
                'Report Settings updated.')
            return http.HttpResponseRedirect(reverse('report_settings'))


    context['settings_nav_active'] = 'active'
    context['report_settings_li'] = 'active'
    context['settings_ul_show'] = 'show'
    context['primary_color'] = primary_color
    context['secondary_color'] = secondary_color

    return render(request, 'scanEngine/settings/report.html', context)


def tool_arsenal_section(request):
    context = {}
    tools = InstalledExternalTool.objects.all().order_by('id')
    context['installed_tools'] = tools
    return render(request, 'scanEngine/settings/tool_arsenal.html', context)


def add_tool(request):
    form = ExternalToolForm()
    if request.method == "POST":
        form = ExternalToolForm(request.POST)
        print(form.errors)
        if form.is_valid():
            # add tool
            install_command = form.data['install_command']
            github_clone_path = None
            if 'git clone' in install_command:
                project_name = install_command.split('/')[-1]
                install_command = install_command + ' /usr/src/github/' + project_name + ' && pip install -r /usr/src/github/' + project_name + '/requirements.txt'
                github_clone_path = '/usr/src/github/' + project_name
                # if github cloned we also need to install requirements, atleast found in the main dir
                install_command = 'pip3 install -r /usr/src/github/' + project_name + '/requirements.txt'

            os.system(install_command)
            run_system_commands.apply_async(args=(install_command,))
            saved_form = form.save()
            if github_clone_path:
                tool = InstalledExternalTool.objects.get(id=saved_form.pk)
                tool.github_clone_path = github_clone_path
                tool.save()

            messages.add_message(
                request,
                messages.INFO,
                'External Tool Successfully Added!')
            return http.HttpResponseRedirect(reverse('tool_arsenal'))
    context = {
            'settings_nav_active': 'active',
            'form': form
        }
    return render(request, 'scanEngine/settings/add_tool.html', context)


def modify_tool_in_arsenal(request, id):
    external_tool = get_object_or_404(InstalledExternalTool, id=id)
    form = ExternalToolForm()
    if request.method == "POST":
        form = ExternalToolForm(request.POST, instance=external_tool)
        if form.is_valid():
            form.save()
            messages.add_message(
                request,
                messages.INFO,
                'Tool modified successfully')
            return http.HttpResponseRedirect(reverse('tool_arsenal'))
    else:
        form.set_value(external_tool)
    context = {
            'scan_engine_nav_active':
            'active', 'form': form}
    return render(request, 'scanEngine/settings/update_tool.html', context)
