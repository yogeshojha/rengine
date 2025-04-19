
# Security Policy

> **[IMPORTANT NOTICE - February 9, 2025]**  
> reNgine is currently undergoing a major refactoring to address all XSS-related vulnerabilities. While we are committed to security, we are temporarily suspending new XSS vulnerability reports until this refactoring is complete. We will continue to accept and investigate all other types of security vulnerabilities. Thank you for your understanding and continued support in making reNgine more secure.
>
> Please note that most reported XSS vulnerabilities in reNgine affect on-premise installations with limited exploitability. Nevertheless, we are committed to fixing these issues systematically through our ongoing refactoring effort.


We appreciate your efforts to responsibly disclose your findings and will make every effort to acknowledge your contributions.

To report a security vulnerability, please follow these steps:

1. **Do Not** disclose the vulnerability publicly on GitHub issues or any other public forum.

2. Go to the [Security tab](https://github.com/yogeshojha/rengine/security) of the reNgine repository.

3. Click on "Report a vulnerability" to open GitHub's private vulnerability reporting form.

4. Provide a detailed description of the vulnerability, including:
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes or mitigations (if you have them)

5. I will review your report and respond as quickly as possible, usually within 48-72 hours.

6. Please allow some time to investigate and address the vulnerability before disclosing it to others.

We are committed to working with security researchers to verify and address any potential vulnerabilities reported to us. After fixing the issue, we will publicly acknowledge your responsible disclosure, unless you prefer to remain anonymous.

Thank you for helping to keep reNgine and its users safe!

**What do we expect from security researchers?**

* Patience: Please note that currently I am the only maintainer in reNgine and will take sometime to validate your report. I request your patience throughout the process.
* Respect Privacy and Security Reports: Please do not disclose any vulnerabilities in public (this also includes github issues) before or after reporting on huntr.dev! That is against the disclosure policy and will not be eligible for monetary rewards.

**What do I get in return?**

* Much thanks from Maintainer and the community
* CVE ID(s)

## Past Security Vulnerabilities

Thanks to these individuals for reporting Security Issues in reNgine.

### 2024

* [HIGH] [Command Injection](https://github.com/yogeshojha/rengine/security/advisories/GHSA-fx7f-f735-vgh4) in Waf Detector, Reported by [n-thumann](https://github.com/n-thumann)
* [MEDIUM] [Stored XSS](https://github.com/yogeshojha/rengine/security/advisories/GHSA-96q4-fj2m-jqf7) in in Vulnerability Page, Reported by [Touhid M Shaikh](https://github.com/touhidshaikh)

### 2022

* [HIGH] [Blind command injection](https://huntr.dev/bounties/b255cf59-9ecd-4255-b9a2-b40b5ec6c572/) in CMS Detector, Reported by [Abdulrahman Abdullah](https://github.com/ph33rr)

* [HIGH] [Command Injection](https://huntr.dev/bounties/00e10ef7-ff5e-450f-84ae-88c793d1a607/) in via Proxy, Reported by [Koen Molenaar](https://github.com/k0enm)

* [HIGH] [Command Injection](https://huntr.dev/bounties/7f1f9abb-a801-444d-bd58-97e1c0b2ddb9/) in via YAML Engine, Reported by [Koen Molenaar](https://github.com/k0enm) and [zongdeiqianxing](https://github.com/zongdeiqianxing)

* [LOW] [Stored XSS](https://huntr.dev/bounties/dfd440ba-4330-413c-8b21-a3d8bf02a67e/) on Import Targets via filename, Reported by [Veshraj Ghimire](https://github.com/V35HR4J)

* [LOW] [Stored XSS](https://huntr.dev/bounties/8ea5d3a6-f857-45e4-9473-e4d9cb8f7c77/) on HackerOne Markdown template, Reported by [Smaran Chand](https://github.com/smaranchand) and [Ayoub Elaich](https://github.com/sicks3c)

* [LOW] [Stored XSS](https://huntr.dev/bounties/6e2b7f19-d457-4e05-b2d5-888110898147/) via Scan Engine Name, Reported by [nerrorsec](https://github.com/nerrorsec)

* [LOW] [HTML Injection](https://huntr.dev/bounties/da2d32a1-8faf-453d-8fa8-c264fd8d7806/) in Subscan, Reported by [nerrorsec](https://github.com/nerrorsec)


### 2021
* [LOW] [Stored XSS](https://github.com/yogeshojha/rengine/issues/178) on Detail Scan Page via Page Title Parameter, Reported by [omemishra](https://github.com/omemishra)

* [LOW] [Stored XSS](https://github.com/yogeshojha/rengine/issues/347) on Vulnerability Scan page via URL Parameter, Reported by [Arif Khan, payloadartist](https://twitter.com/payloadartist)

* [LOW] Several Instances of XSS in reNgine 1.0 (#460, #459, #458, #457, #456, #455), Reported by [Binit Ghimire](https://github.com/TheBinitGhimire)

* [LOW] [Stored XSS](https://huntr.dev/bounties/ac07ae2a-1335-4dca-8d55-64adf720bafb/) on GF Pattern via filename, Reported by [nerrorsec](https://github.com/nerrorsec)

* [LOW] [Stored XSS](https://huntr.dev/bounties/0f8de2a4-7590-48f1-a5af-1e2cab9f6e85/) on Delete Scheduled Task via Scan Engine Name, Reported by [nerrorsec](https://github.com/nerrorsec)

* [LOW] [Stored XSS](https://huntr.dev/bounties/693a7d23-c5d4-448e-bbf6-50b3f0ad8544/) on Target Summary via Todo, Reported by [TheLabda](https://github.com/thelabda)

* [LOW] [Stored XSS](https://huntr.dev/bounties/81c48a07-9cb8-4da8-babc-28a4076a5e92/) on Nuclei Template Summary via malicious Nuclei Template, Reported by [Walleson Moura](https://github.com/phor3nsic)

* [MEDIUM] [Path Traversal/LFI](https://huntr.dev/bounties/5df1a485-7a1e-411d-9664-0f4343e8512a/), reported by [Koen Molenaar](https://github.com/k0enm)
