# Changelog

## 🏷️ 1.0.1 [Current Release]

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

#### Features/Additions
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

#### Features
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

#### Abandoned
- Subdomain Takeover: As we decided to use Nuclei for Vulnerability Scanner, and also, since Subjack wasn't giving enough results, I decided to remove Subjack. The subdomain Takeover will now be part of Nuclei Vulnerability Scanner.

### V0.4 Release 2020-10-08

#### Features
- Background tasks migrated to Celery and redis
- Periodic and clocked scan added
- Ability to Stop and delete the scan
- CNAME and IP address added on detail scan
- Content type added on Endpoints section
- Ability to initiate multiple scans at a time

### V0.3 Release 2020-07-21

#### Features
- YAML based Customization Engine
- Ability to add wordlists
- Login Feature

### V0.2 Release 2020-07-11

#### Features
- Directory Search Enabled
- Fetch URLS using hakrawler
- Subdomain takeover using Subjack
- Add Bulk urls
- Delete Scan functionality

#### Fix
- Windows Installation issue fixed
- Scrollbar Issue on small screens fixed

### V0.1 Release 2020-07-08
- reNgine is released
