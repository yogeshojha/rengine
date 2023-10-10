# Changelog


## 2.0.0

**Release Date: October 7, 2023**

###  Added
 - Projects: Projects allow you to efficiently organize their web application reconnaissance efforts. With this feature, you can create distinct project spaces, each tailored to a specific purpose, such as personal bug bounty hunting, client engagements, or any other specialized recon task.
 - Roles and Permissions: assign distinct roles to your team members: Sys Admin, Penetration Tester, and Auditor—each with precisely defined permissions to tailor their access and actions within the reNgine ecosystem.
 - GPT-powered Report Generation: With the power of OpenAI's GPT, reNgine now provides you with detailed vulnerability descriptions, remediation strategies, and impact assessments.
 - API Vault: This feature allows you to organize your API keys such as OpenAI or Netlas API keys.
 - GPT-powered Attack Surface Generation
 - URL gathering now is much more efficient, removing duplicate endpoints based on similar HTTP Responses, having the same content_lenth, or page_title. Custom duplicate fields can also be set from the scan engine configuration.
 - URL Path filtering while initiating scan: For instance, if we want to scan only endpoints starting with https://example.com/start/, we can pass the /start as a path filter while starting the scan. [@ocervell](https://github.com/ocervell)
 - Expanding Target Concept: reNgine 2.0 now accepts IPs, URLS, etc as targets. (#678, #658) Excellent work by [@ocervell](https://github.com/ocervell)
 - A ton of refactoring on reNgine's core to improve scan efficiency. Massive kudos to [@ocervell](https://github.com/ocervell)
 - Created a custom celery workflow to be able to run several tasks in parallel that are not dependent on each other, such OSINT task and subdomain discovery will run in parallel, and directory and file fuzzing, vulnerability scan, screenshot gathering etc. will run in parallel after port scan or url fetching is completed. This will increase the efficiency of scans and instead of having one long flow of tasks, they can run independently on their own. [@ocervell](https://github.com/ocervell)
 - Refactored all tasks to run asynchronously [@ocervell](https://github.com/ocervell)
 - Added a stream_command that allows to read the output of a command live: this means the UI is updated with results while the command runs and does not have to wait until the task completes. Excellent work by [@ocervell](https://github.com/ocervell)
 - Pwndb is now replaced by h8mail. [@ocervell](https://github.com/ocervell)
 - Group Scan Results: reNgine 2.0 allows to group of subdomains based on similar page titles and HTTP status, and also vulnerability grouping based on the same vulnerability title and severity.
 - Added Support for Nmap: reNgine 2.0 allows to run Nmap scripts and vuln scans on ports found by Naabu. [@ocervell](https://github.com/ocervell)
 - Added support for Shared Scan Variables in Scan Engine Configuration:
    - `enable_http_crawl`: (true/false) You can disable it to be more stealthy or focus on something different than HTTP
    - `timeout`: set timeout for all tasks
    - `rate_limit`: set rate limit for all tasks
    - `retries`: set retries for all tasks
    - `custom_header`: set the custom header for all tasks
 - Added Dalfox for XSS Vulnerability Scan
 - Added CRLFuzz for CRLF Vulnerability Scan
 - Added S3Scanner for scanning misconfigured S3 buckets
 - Improve OSINT Dork results, now detects admin panels, login pages and dashboards
 - Added Custom Dorks
 - Improved UI for vulnerability results, clicking on each vulnerability will open up a sidebar with vulnerability details.
 - Added HTTP Request and Response in vulnerability Results
 - Under Admin Settings, added an option to allow add/remove/deactivate additional users
 - Added Option to Preview Scan Report instead of forcing to download
 - Added Katana for crawling and spidering URLs
 - Added Netlas for Whois and subdomain gathering
 - Added TLSX for subdomain gathering
 - Added CTFR for subdomain gathering
 - Added historical IP in whois section
 - Added Pagination on Large datatables such as subdomains, endpoints, vulnerabilities etc #949 [@psyray](https://github.com/psyray)


### Fixes
 - GF patterns do not run on 404 endpoints (#574 closed)
 - Fixes for retrieving whois data (#693 closed)
 - Related/Associated Domains in Whois section is now fixed
 - Fixed missing lightbox css & js on target screenshot page #947 #948 [@psyray](https://github.com/psyray)
 - Issue in Port-scan: int object is not subscriptable Fixed #939, #938 [@AnonymousWP](https://github.com/AnonymousWP)


### Removed
 - Removed pwndb and tor related to it.
 - Removed tor for pwndb


## 1.3.6
**Release Date: March 2, 2023**

- Fixed installation errors. Fixed #824, #823, #816, #809, #803, #801, #798, #797, #794, #791 .


## 1.3.5
**Release Date: December 29, 2022**

- Fixed #769, #768, #766, #761, Thanks to, @bin-maker, @carsonchan12345, @paweloque, @opabravo


## 1.3.4
**Release Date: November 16, 2022**

### Fixes
- Fixed #748 , #743 , #738, #739


## 1.3.3
**Release Date: October 9, 2022**

### Fixes
- #723, Upgraded Go to 1.18.2


## 1.3.2
**Release Date: August 20, 2022**

### Fixes
- #683 For Filtering GF tags
- #669 Where Directory UI had to be collapsed


## 1.3.1
**Release Date: August 12, 2022**

### Fixes
- Fix for #643 Downloading issue for Subdomain and Endpoints
- Fix for #627 Too many Targets causes issues while loading datatable
- Fix version Numbering issue


## 1.3.0
**Release Date: July 11, 2022**

### Added

- Geographic Distribution of Assets Map
- Added WAF Detector as an optional tool in Scan Engine

### Fixes

- WHOIS Provider Changed
- Fixed Dark UI Issues
- Fix HTTPX Issue with custom Header

## 1.2.0
**Release Date: May 27, 2022**

### Added

- Naabu Exclude CDN Port Scanning
- Added WAF Detection

### Fixes

- Fix #630 Character Name too Long Issue
- [Security] Fixed several instances of Command Injections, CVE-2022-28995, CVE-2022-1813
- Hakrawler Fixed - #623
- Fixed XSS on Hackerone report via Markdown
- Fixed XSS on Import Target using malicious filename
- Stop Scan Fixed #561
- Fix installation issue due to missing curl
- Updated docker-compose version

## 🏷️ 1.1.0
**Release Date: Apr 24, 2022**

- Redeigned UI
- Added Subscan Feature

    Subscan allows further scanning any subdomains. Assume from a normal recon process you identified a subdomain that you wish to do port scan. Earlier, you had to add that subdomain as a target. Now you can just select the subdomain and initiate subscan.

- Ability to Download reconnaissance or vulnerability report
- Added option to customize report, customization includes the look and feel of report, executive summary etc.

- Add IP Address from IP
- WHOIS Addition on Detail Scan and fetch whois automatically on Adding Single Targets
- Universal Search Box
- Addition of Quick Add menus
- Added ToolBox Feature

    ToolBox will feature most commonly used recon tools. One can use these tools to identify whois, CMSDetection etc without adding targets. Currently, Whois, CMSDetector and CVE ID lookup is supported. More tools to follow up.

- Notify New Releases on reNgine if available
- Tools Arsenal Section to feature preinstalled and custom tools
- Ability to Update preinstalled tools from Tools Arsenal Section
- Ability to download/add custom tools
- Added option for Custom Header on Scan Engine
- Added CVE_ID, CWE_ID, CVSS Score, CVSS Metrics on Vulnerability Section, this also includes lookup using cve_id, cwe_id, cvss_score etc
- Added curl command and references on Vulnerability Section
- Added Columns Filtering Option on Subdomain, Vulnerability and Endpoints Tables
- Added Error Handling for Failed Scans, reason for failure scan will be displayed
- Added Related Domains using WHOIS
- Added Related TLDs
- Added HTTP Status Breakdown Widget
- Added CMS Detector
- Updated Visualization
- Option to Download Selected Subdomains
- Added additional Nuclei Templates from https://github.com/geeknik/the-nuclei-templates
- Added SSRF check from Nagli Nuclei Template
- Added option to fetch CVE_ID details
- Added option to Delete Multiple Scans
- Added ffuf as Directory and Files fuzzer
- Added widgets such as Most vulnerable Targets, Most Common Vulnerabilities, Most Common CVE IDs, Most Common CWE IDs, Most Common Vulnerability Tags

And more...

## 🏷️ 1.0.1

**Release Date: Aug 29, 2021**

**Changelog**

- Fixed [#482](https://github.com/yogeshojha/rengine/issues/482) Endpoints and Vulnerability Datatable were showing results of other targets due to the scan_id parameter
- Fixed [#479](https://github.com/yogeshojha/rengine/issues/479) where the scan was failing due to recent httpx release, change was in the JSON output
- Fixed [#476](https://github.com/yogeshojha/rengine/issues/476) where users were unable to click on Clocked Scan (Reported only on Firefox)
- Fixed [#442](https://github.com/yogeshojha/rengine/issues/442) where an extra slash was added in Directory URLs
- Fixed [#337](https://github.com/yogeshojha/rengine/issues/337) where users were unable to link custom wordlist
- Fixed [#436](https://github.com/yogeshojha/rengine/issues/436) Checkbox in Notification Settings were not working due to same name attribute, now fixed
- Fixed [#439](https://github.com/yogeshojha/rengine/issues/439) Hakrawler crashed if the deep mode was activated due to -plain flag
- Fixed [#437](https://github.com/yogeshojha/rengine/issues/437) If Out of Scope subdomains were supplied, the scan was failing due to None value
- Fixed [#424](https://github.com/yogeshojha/rengine/issues/424) Multiple Targets couldn't be scanned

**Improvements**

- Enhanced install script, check for if docker is running service or not #468

**Security**

- Fixed Cross Site Scripting
    - [#460](https://github.com/yogeshojha/rengine/issues/460)
    - [#457](https://github.com/yogeshojha/rengine/issues/457)
    - [#454](https://github.com/yogeshojha/rengine/issues/454)
    - [#453](https://github.com/yogeshojha/rengine/issues/453)
    - [#459](https://github.com/yogeshojha/rengine/issues/459)
    - [#460](https://github.com/yogeshojha/rengine/issues/460)
- Fixed Cross Site Scripting reported on Huntr [#478](https://github.com/yogeshojha/rengine/issues/478)
    [https://www.huntr.dev/bounties/ac07ae2a-1335-4dca-8d55-64adf720bafb/](https://www.huntr.dev/bounties/ac07ae2a-1335-4dca-8d55-64adf720bafb/)

### Verion 1.0 Major release

### Additions
- Dark Mode
- Recon Data visualization
- Improved correlation among recon data
- Ability to identify Interesting Subdomains
- Ability to Automatically report Vulnerabilities to Hackerone with customizable vulnerability report
- Added option to download URLs and Endpoints along with matched GF patterns
- Dorking support for stackoverflow, 3rdparty, social_media, project_management, code_sharing, config_files, jenkins, wordpress_files, cloud_buckets, php_error, exposed_documents, struts_rce, db_files, traefik, git_exposed
- Emails, metainfo, employees, leaked password discovery
- Optin to Add bulk targets
- Proxy Support
- Target Summary
- Recon Todo
- Unusual Port Identification
- GF patterns support #110, #88
- Screenshot Gallery with Filters
- Powerful recon data filtering with auto suggestions
- Added whatportis, this allows ports to be displayed as Service Name and Description
- Recon Data changes, finds new/removed subdomains/endpoints
- Tagging of targets into Organization
- Added option to delete all scan results or delete all screenshots inside Settings and reNgine settings
- Support for custom GF patterns and Nuclei Templates
- Support for editing tool related configuration files (Nuclei, Subfinder, Naabu, amass)
- Option to Mark Subdomains as important
- Separate tab for Directory scan results
- Option to Import Subdomains
- Clean your scan results and screenshots
- Enhanced and Customizable Scan alert with support for sending recon data directly to Discord
- Improvement in Vulnerability Scanning, If endpoint scan is performed, those endpoints will be an input to Nuclei.
- Ignore file extensions in URLs
- Added response time in endpoints and subdomains
- Added badge to identify CDN and non CDN IPs
- Added gospider, gauplus and waybackurls for url discovery
- Added activity log in Scan activity
- For better UX shifted nav bar from vertical position to horizontal position on top. This allows better navigation on recon data.
- Separate table for Directory scan results #244
- Scan results UI now in tabs
- Added badge on Subdomain Result table to directly query Vulnerability and Endpoints
- Webserver and content_type badge has been addeed in Subdomain Result table
- Inside Targets list, Recent Scan button has been added to quickly go to the last scan results
- In target summary, timelin of scan has been added
- Randomized user agent in HTTPX
- reNgine will no longer store any recon data apart from that in Database, this includes sorted_subdomains list.txt or any json file
- aquatone has been replaced with Eyewitness
- Out of Scope subdomains are no longer part of scan engine, they can be imported before initiating the scan
- Added script to uninstall reNgine
- Added option to filter targets and scans using organization, scan status, etc
- Added random user agent in directory scan
- Added concurrency, rate limit, timeout, retries in Scan Engine YAML
- Added Rescan option
- Other tiny fixes.....

### V0.5.3 Feb25 2021
- Build error for Naabu v2 Fixed
- Added rate support for Naabu

### V0.5.2 Feb 23 2021
- Fixed XSS https://github.com/yogeshojha/rengine/issues/347

### V0.5.1 Feb 19 2021

### Features
- Added Discord Support for Notification Web hooks

### V0.5 29 Nov 2020

### Features
- Nuclei Integration: v0.5 is primarily focused on vulnerability scanner using Nuclei. This was a long pending due and we've finally integrated it.

- Powerful search queries across endpoints, subdomains and vulnerability scan results: reNgine reconnaissance data can now be queried using operators like <,>,&,| and !, namely greater than, less than, and, or, and not. This is extremely useful in querying the recon data. More details can be found at Instructions to perform Queries on Recon data

- Out of scope options: Many of you have been asking for out of scope option. Thanks to Valerio Brussani for his pull request which made it possible for out of scope options. Please check the documentation on how to define out of scope options.

- Official Documentation(WIP): We often get asked on how to use reNgine. For long, we had no official documentation. Finally, I've worked on it and we have the official documentation at rengine.wiki

- The documentation is divided into two parts, for Developers and for Penetration Testers. For developers, it's a work in progress. I will keep you all updated throughout the process.

- Redefined Dashboard: We've also made some changes in the Dashboard. The additions include vulnerability scan results, most vulnerable targets, most common vulnerabilities.

- Global Search: This feature has been one of the most requested features for reNgine. Now you can search all the subdomains, endpoints, and vulnerabilities.

- OneForAll Support: reNgine now supports OneForAll for subdomain discovery, it is currently in beta. I am working on how to integrate OneForAll APIKeys and Configuration files.

- Configuration Support for subfinder: You will now have ability to add configurations for subfinder as well.

- Timeout option for aquatone: We added timeout options in yaml configuration as a lot of screenshots were missing. You can now define timeout for http, scan and screenshots for timeout in milliseconds.

- Design Changes A lot of design changes has happened in reNgine. Some of which are:

- Endpoints Results and Vulnerability Scan Results are now displayed as a separate page, this is to separate the results and decrease the page load time.
Checkbox next to Subdomains and Vulnerability report list to change the status, this allows you to mark all subdomains and vulnerabilities that you've already completed working on.
- Sometimes due to timeout, aquatone was skipping the screenshots and due to that, navigations between screenshots was little annoying. We have fixed it as well.
Ability to delete multiple targets and initiate multiple scans.

### Abandoned
- Subdomain Takeover: As we decided to use Nuclei for Vulnerability Scanner, and also, since Subjack wasn't giving enough results, I decided to remove Subjack. The subdomain Takeover will now be part of Nuclei Vulnerability Scanner.

### V0.4 Release 2020-10-08

### Features
- Background tasks migrated to Celery and redis
- Periodic and clocked scan added
- Ability to Stop and delete the scan
- CNAME and IP address added on detail scan
- Content type added on Endpoints section
- Ability to initiate multiple scans at a time

### V0.3 Release 2020-07-21

### Features
- YAML based Customization Engine
- Ability to add wordlists
- Login Feature

### V0.2 Release 2020-07-11

### Features
- Directory Search Enabled
- Fetch URLS using hakrawler
- Subdomain takeover using Subjack
- Add Bulk urls
- Delete Scan functionality

### Fix
- Windows Installation issue fixed
- Scrollbar Issue on small screens fixed

### V0.1 Release 2020-07-08
- reNgine is released
