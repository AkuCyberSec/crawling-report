# Crawling Report
Create an interactive HTML report from a list of URLs to help identifying interesting URLs based on configurable rules. 

Run: **run.py \<arg\>**  
**Arguments:**
- get-config: Create a copy of config.yaml in **/app/out**
- create-report: Generate the HTML report in **/app/out**

If no argument is specified, it prints out the help.

## How To (Dockerized version)
1) Create a config.yaml file and put it in the same directory of run.sh.
2) Edit run.sh and modify the volumes pointing to /app/in (Input folder) and /app/out (Output folder).
3) Run run.sh

The input folder **/app/in** must contain at least one file that contains a list of URLs (one per line).
The tool will process every file (it uses **cat** and **grep** commands).  
After processing, the tool will produce an HTML report in the output folder **/app/out** along with its dependencies (JS and CSS files).

## Templates
Files are in the template folder: **/app/template**.  
It's possible to edit HTML, JS and CSS files without rebuilding, by adding a volume that points to /app/template.

## Config.yaml
The configuration file must have the following structure:
```yaml
rules:
  - name: "Credentials"
    matchers:
      # Users and passwords
      - "[\\?|&](passw|pwd|password|passwd|username|user|usr|login|loginid)=[^&]"
    extractors:
      - name: "Password"
        group: 2
        expression: "(passw|pwd|password|passwd)=([^&]+)"
```

Under **rules** we have:
- **name**: The name of the rule
- **matchers**: A list of regular expressions used with the **grep** command (grep -iE '\<regexp\>') for extracting URLs from lists that match the regular expressions.
- **extractors**: A list of extractors that define regular expressions in **JavaScript**, in the HTML report. The extractors are used for extracting values from single URLs.  

The structure of an extractor is the following:
- **name**: The name of the extractor.
- **group**: The ID of the group defined in the expression that contains the value to be shown.
- **expression**: The regular expression

A group in a regular expression is defined by using parentheses.

### Config Example
Let's say we have the following URLs:
```
matcher: [\\?|&](passw|pwd|password|passwd|username|user|usr|login|loginid)=[^&]

URLs:
https://evil-site.com/login.php?user=guest&password=Passw0rd!
https://evil-site.com/search.php?id=1
```

The **matcher** defined above will match the first URL only.
After creating the HTML report, the extractor "Password" will match a specific pair of parameter/value:
```
extractor expression: (passw|pwd|password|passwd)=([^&]+)

extracted values:
group 0: password=Passw0rd!
group 1: password
group 2: Passw0rd!
```

Since the value of **group** in the YAML file is **2**, in our report we will have the value **Passw0rd!** under the column **Values**.  
We can specify the group **0** if we want our report to display both the parameter and its value.

![alt text](example.png)

# Example
On our host we have two folders:
- **/home/kali/report/input** as our input folder
- **/home/kali/report/output** as our output folder

1. Edit the **run.sh** file and modify the following volumes:
```bash
change
-v "$(pwd)/sample_input":"/app/in"
-v "$(pwd)/sample_output":"/app/out"

to
-v "/home/kali/report/input/":"/app/in"
-v "/home/kali/report/output/":"/app/in"
```

2. Edit the **config.yaml** to add, remove or modify rules.  
3. Create a list of URLs (you can do it manually or create it using tools such as **waybackurls** or **Katana**) and save it in the input folder.  
4. Run the script **run.sh**
5. Open the HTML report in the output folder.

HTML reports can be exported in TXT and CSV formats.  
**Exported files will contain only visible rows.**  