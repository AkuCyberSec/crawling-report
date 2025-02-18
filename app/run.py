#!/usr/bin/python
import yaml, logging, os, sys, shutil, json
from datetime import datetime

INPUT_DIRECTORY = "in"
OUTPUT_DIRECTORY = "out"
CACHE_DIRECTORY_NAME = "cache"
CACHE_DIRECTORY_FULL_PATH = f'{OUTPUT_DIRECTORY}/{CACHE_DIRECTORY_NAME}'
CONFIG_FILE_DIRECTORY = "."
CONFIG_FILE_NAME = "config.yaml"
CONFIG_FILE_FULL_PATH = f'{CONFIG_FILE_DIRECTORY}/{CONFIG_FILE_NAME}'

logger = logging.getLogger(__name__)

class CachedRule:
    name:str = None
    extracted_urls:list[str] = None
    processed_matchers:list[str] = None

    def __init__(self, cache_name:str):
        self.name = cache_name
        self.extracted_urls = []
        self.processed_matchers = []
        self.__load_cache()

    def add_urls_and_matcher_to_cache(self, urls:list[str], matcher:str):
        self.extracted_urls = urls
        self.processed_matchers.append(matcher)
        self.__save_cache()
    
    def is_matcher_already_processed(self, matcher:str):
        return matcher in self.processed_matchers
    
    def __get_url_cache_full_path(self):
        return f'{CACHE_DIRECTORY_FULL_PATH}/{self.name}.cache'
    
    def __load_cache(self):
        if not os.path.isfile(self.__get_url_cache_full_path()):
            return
        
        logger.info(f"Loading caches for rule {self.name}")
        with open(f'{self.__get_url_cache_full_path()}', 'r') as cache_file:
            cache_json = json.load(cache_file)
            self.extracted_urls = cache_json["extracted_urls"]
            self.processed_matchers = cache_json["processed_matchers"]
            logger.info(f"Loaded {len(self.extracted_urls)} extracted urls and {len(self.processed_matchers)} processed matchers.")
        
    def __save_cache(self):

        if not os.path.isdir(CACHE_DIRECTORY_FULL_PATH):
            logger.debug(f"Directory {CACHE_DIRECTORY_FULL_PATH} does not exists. Creating it...")
            os.mkdir(CACHE_DIRECTORY_FULL_PATH)

        cache_json = {
            "name" : self.name,
            "extracted_urls" : self.extracted_urls,
            "processed_matchers" : self.processed_matchers
        }

        logger.info(f"Saving caches for rule {self.name} ({len(self.extracted_urls)} extracted urls; {len(self.processed_matchers)} processed matchers)")
        with open(f'{self.__get_url_cache_full_path()}', 'w') as cache_file:
            json.dump(cache_json, cache_file)


class Extractor:
    name:str = None
    group:int = 0
    expression:str = None
    
    def __init__(self, name:str, group:int, expression:str):
        self.name = name
        self.group = group
        self.expression = expression

class Rule:
    name:str = None
    matchers:list[str] = []
    extractors:list[Extractor] = []
    results:list[str] = None
    cache:CachedRule = None

    def __init__(self, name:str, matchers:list[str], extractors:list[Extractor]):
        self.name = name
        self.matchers = matchers
        self.extractors = extractors
        self.cache = CachedRule(name)
        self.results = self.cache.extracted_urls

    def match_results(self, input_directory:str):
        logger.info(f"Extraction started for rule \"{self.name}\"")
        for matcher in self.matchers:
            if self.cache.is_matcher_already_processed(matcher):
                logger.debug(f"Matcher {matcher} already processed. It will be skipped ")
                continue

            logger.debug(f"Extracting using the following matcher: {matcher}")
            results = os.popen(f"cat {input_directory}/* | grep -iE '{matcher}' | sort -u").readlines()
            logger.debug(f"Number of results: {len(results)}")
            self.results += results
            self.cache.add_urls_and_matcher_to_cache(self.results, matcher)
        logger.debug(f"Number of results for rule {self.name} after grep: {len(self.results)}")

    def get_all_extractors_for_html_report(self, extractor_template:str) -> str:
        extractors:list[str] = []
        logger.info(f"Getting extractors for report for rule {self.name}")
        logger.debug(f"Number of extractors: {len(self.extractors)}")
        counter:int = 2
        for extractor in self.extractors:
            extractors.append(extractor_template \
                .replace("@@EXTRACTOR_EXPRESSION", extractor.expression) \
                .replace("@@EXTRACTOR_GROUP", str(extractor.group))
                .replace("@@EXTRACTOR_NAME", extractor.name)
                .replace("@@COUNTER", str(counter)))
            counter += 1

        return "\n".join(extractors)
    
    def get_all_rows_for_html_report(self, row_template:str) -> str:
        rows:list[str] = []
        logger.info(f"Getting rows for report for rule {self.name}")
        logger.debug(f"Number of results: {len(self.results)}")
        self.results = sorted(set(self.results))
        for result in self.results:
            rows.append(row_template.replace("@@FULL_URL", result.strip()))
        return "\n".join(rows)
    
class CrawlingReport:

    # YAML Keys
    OBJECT_NAME_KEY = "name"
    RULE_MATCHERS_KEY = "matchers"
    RULE_OUTPUT_FILENAME_KEY = "output_filename"
    RULE_EXTRACTORS_KEY = "extractors"
    EXTRACTOR_GROUP_KEY = "group"
    EXTRACTOR_EXPRESSION_KEY = "expression"

    # Directories
    TEMPLATE_DIRECTORY = "template"

    # Variables
    rules:list[Rule] = []

    def __init__(self, config_file:str):
        logger.info(f"Reading configuration file: {config_file}")
        with open(config_file) as yaml_file_stream:
            yaml_rules = yaml.load(yaml_file_stream, yaml.FullLoader)["rules"]
            for yaml_rule in yaml_rules:
                rule_name = yaml_rule[CrawlingReport.OBJECT_NAME_KEY]
                matchers = yaml_rule[CrawlingReport.RULE_MATCHERS_KEY]
                yaml_extractors = yaml_rule[CrawlingReport.RULE_EXTRACTORS_KEY]
                extractors:list[Extractor] = []
                for yaml_extractor in yaml_extractors:
                    extractor_name = yaml_extractor[CrawlingReport.OBJECT_NAME_KEY]
                    extractor_group = yaml_extractor[CrawlingReport.EXTRACTOR_GROUP_KEY]
                    extractor_expression = yaml_extractor[CrawlingReport.EXTRACTOR_EXPRESSION_KEY]
                    extractors.append(Extractor(extractor_name, extractor_group, extractor_expression))
                self.rules.append(Rule(rule_name, matchers, extractors))

    def apply_rules(self, input_directory:str):
        for rule in self.rules:
            rule.match_results(input_directory)
    
    # region HTMLReport
    def create_html_report(self, output_directory:str):
        base_template:str = self.__load_base_template()
        panel_template:str = self.__load_panel_template()
        extractor_template:str = self.__load_extractor_template()
        row_template:str = self.__load_row_template()
        panels:list[str] = []

        for rule in self.rules:
            extractors:str = rule.get_all_extractors_for_html_report(extractor_template)
            rows:str = rule.get_all_rows_for_html_report(row_template)
            panels.append(panel_template \
                    .replace("@@RULE_NAME", rule.name) \
                    .replace("@@EXTRACTORS", extractors) \
                    .replace("@@ROWS", rows))
    
        filename:str = f"report_{datetime.now().strftime("%Y%m%d%H%M%S")}.html"
        output:str = base_template.replace("@@PANELS", "\n".join(panels))
        with open(f'{output_directory}/{filename}', "w") as output_file:
            output_file.write(output)
        
        self.__copy_dependencies_to_output_directory(output_directory)
    def __copy_dependencies_to_output_directory(self, output_directory:str):
        shutil.copyfile(f"{CrawlingReport.TEMPLATE_DIRECTORY}/script.js", f"{output_directory}/script.js")
        shutil.copyfile(f"{CrawlingReport.TEMPLATE_DIRECTORY}/style.css", f"{output_directory}/style.css")
        shutil.copyfile(f"{CrawlingReport.TEMPLATE_DIRECTORY}/tailwind.js", f"{output_directory}/tailwind.js")  
    def __load_base_template(self) -> str:
        with open(f"{CrawlingReport.TEMPLATE_DIRECTORY}/base_template.html", "r") as base_template:
            return base_template.read()
    def __load_panel_template(self) -> str:
        with open(f"{CrawlingReport.TEMPLATE_DIRECTORY}/panel_template.html", "r") as panel_template:
            return panel_template.read()
    def __load_extractor_template(self) -> str:
        with open(f"{CrawlingReport.TEMPLATE_DIRECTORY}/extractor_template.html", "r") as extractor_template:
            return extractor_template.read()    
    def __load_row_template(self) -> str:
        with open(f"{CrawlingReport.TEMPLATE_DIRECTORY}/row_template.html", "r") as row_template:
            return row_template.read()
    # endregion

def print_help():
    print("===== Crawling Report =====")
    print("Create an interactive HTML report from a list of URLs to help identifying interesting URLs based on configurable rules.")
    print("")
    print("run.py <arg>")
    print("Arguments:")
    print("get-config: Create a copy of config.yaml in /app/out")
    print("create-report: Generate the HTML report in /app/out. Use cached results (if they exist).")
    print("create-report-no-cache: Generate the HTML report in /app/out. Ignore cached results.")
    print("")
    print("===== How To (Dockerized version) =====")
    print("1) Create a config.yaml file and put it in the same directory of run.sh.")
    print("2) Edit run.sh and modify the volumes pointing to /app/in (Input folder) and /app/out (Output folder).")
    print("3) Run run.sh")
    print("")
    print("The input folder (/app/in) must contain at least one file that contains a list of URLs (one per line).")
    print("The tool will process every file (it uses cat and grep commands).")
    print("After processing, the tool will produce an HTML report in the output folder (/app/out) along with its dependencies (JS and CSS files).")
    print("")
    print("===== Template =====")
    print("Files are in the template folder: /app/template.")
    print("It's possible to edit HTML, JS and CSS files without rebuilding, by adding a volume that points to /app/template.")
    
def get_default_config_file(config_file_path:str):
    logger.info(f"Copying {config_file_path} to {OUTPUT_DIRECTORY}")
    shutil.copy(config_file_path, f'{OUTPUT_DIRECTORY}/{CONFIG_FILE_NAME}')
    exit()

def delete_cache():
    logger.info(f"Deleting cache in {CACHE_DIRECTORY_FULL_PATH}")
    shutil.rmtree(CACHE_DIRECTORY_FULL_PATH)

def main():
    file_handler = logging.FileHandler(f"{OUTPUT_DIRECTORY}/crawlingreport_log.log")
    stream_handler = logging.StreamHandler(sys.stdout)
    logging.basicConfig(level=logging.DEBUG, handlers= [file_handler, stream_handler])

    try:

        if len(sys.argv) != 2:
            print_help()
            exit()
        
        if sys.argv[1] == "get-config":
            get_default_config_file(CONFIG_FILE_FULL_PATH)
        elif sys.argv[1] == "create-report" or sys.argv[1] == "create-report-no-cache":
            if sys.argv[1] == "create-report-no-cache":
                delete_cache()
            crawling_report = CrawlingReport(CONFIG_FILE_FULL_PATH)
            logger.info("Applying rules...")
            crawling_report.apply_rules(INPUT_DIRECTORY)
            logger.info("Creating HTML report...")
            crawling_report.create_html_report(OUTPUT_DIRECTORY)
            logger.info("Report created successfully!")
        else:
            print_help()

    except Exception as excp:
        logger.exception(excp)

if __name__ == '__main__':
    main()