#!/usr/bin/python
import yaml, logging, os, sys, shutil, json, math
from datetime import datetime
from urllib.parse import urlparse

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
    rows:list[str] = None
    cache:CachedRule = None
    is_enabled:bool = False

    def __init__(self, name:str, matchers:list[str], extractors:list[Extractor], is_enabled:bool):
        self.name = name
        self.matchers = matchers
        self.extractors = extractors
        if not is_enabled:
            logger.info(f"Caches won't be loaded for rule {name} because is not enabled.")
            self.cache = None
            self.rows = []
        else:
            self.cache = CachedRule(name)
            self.rows = self.cache.extracted_urls
        self.is_enabled = is_enabled

    def match_results(self, input_directory:str):
        if not self.is_enabled:
            logger.info(f"Rule {self.name} is not enabled. Extraction will be skipped.")
            return
        
        logger.info(f"Extraction started for rule \"{self.name}\"")
        for matcher in self.matchers:
            if self.cache.is_matcher_already_processed(matcher):
                logger.debug(f"Matcher {matcher} already processed. It will be skipped ")
                continue

            logger.debug(f"Extracting using the following matcher: {matcher}")
            results = os.popen(f"cat {input_directory}/* | grep -iE '{matcher}' | sort -u").readlines()
            logger.debug(f"Number of results: {len(results)}")
            self.rows += results
            self.cache.add_urls_and_matcher_to_cache(self.rows, matcher)
        logger.debug(f"Number of results for rule {self.name} after grep: {len(self.rows)}")

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

class CrawlingReport:

    # YAML Keys
    OBJECT_NAME_KEY = "name"
    RULES_KEY = "rules"
    MAX_ROWS_PER_REPORT_KEY = "max_rows_per_report"
    HIDE_ROWS_AUTOMATICALLY_KEY = "hide_rows_automatically"
    RULE_MATCHERS_KEY = "matchers"
    RULE_OUTPUT_FILENAME_KEY = "output_filename"
    RULE_EXTRACTORS_KEY = "extractors"
    RULE_IS_ENABLED_KEY = "enabled"
    EXTRACTOR_GROUP_KEY = "group"
    EXTRACTOR_EXPRESSION_KEY = "expression"

    # Directories
    TEMPLATE_DIRECTORY = "template"

    # Variables
    rules:list[Rule] = []
    max_rows_per_report:int = 1
    hide_rows_automatically:bool = False

    def __init__(self, config_file:str):
        logger.info(f"Reading configuration file: {config_file}")
        with open(config_file) as yaml_file_stream:
            yaml_file = yaml.load(yaml_file_stream, yaml.FullLoader)
            self.max_rows_per_report = yaml_file[CrawlingReport.MAX_ROWS_PER_REPORT_KEY]
            self.hide_rows_automatically = yaml_file[CrawlingReport.HIDE_ROWS_AUTOMATICALLY_KEY]
            yaml_rules = yaml_file[CrawlingReport.RULES_KEY]

            for yaml_rule in yaml_rules:
                rule_name = yaml_rule[CrawlingReport.OBJECT_NAME_KEY]
                is_rule_enabled = yaml_rule[CrawlingReport.RULE_IS_ENABLED_KEY]
                matchers = yaml_rule[CrawlingReport.RULE_MATCHERS_KEY]
                yaml_extractors = yaml_rule[CrawlingReport.RULE_EXTRACTORS_KEY]
                extractors:list[Extractor] = []
                for yaml_extractor in yaml_extractors:
                    extractor_name = yaml_extractor[CrawlingReport.OBJECT_NAME_KEY]
                    extractor_group = yaml_extractor[CrawlingReport.EXTRACTOR_GROUP_KEY]
                    extractor_expression = yaml_extractor[CrawlingReport.EXTRACTOR_EXPRESSION_KEY]
                    extractors.append(Extractor(extractor_name, extractor_group, extractor_expression))
                self.rules.append(Rule(rule_name, matchers, extractors, is_rule_enabled))

    def apply_rules(self, input_directory:str):
        for rule in self.rules:
            rule.match_results(input_directory)

    def create_html_reports(self, output_directory:str):
        if self.max_rows_per_report < 1:
            raise Exception(f"A report must include at least one row (max_rows_per_report > 0). Value: {self.max_rows_per_report}")
        
        panel_template:str = self.__load_panel_template()
        extractor_template:str = self.__load_extractor_template()
        row_template:str = self.__load_row_template()
        report_base_filename:str = f"report_{datetime.now().strftime("%Y%m%d%H%M%S")}"

        total_number_of_rows:int = 0
        for rule in self.rules:
            if rule.is_enabled:
                total_number_of_rows += len(rule.rows)

        total_row_counter:int = 0
        report_row_counter:int = 0
        report_counter:int = 0
        panels:list[str] = []
        rows:list[str] = []
        hostnames:list[str] = []

        expected_number_of_reports_to_be_generated:int = math.ceil(total_number_of_rows / self.max_rows_per_report)
        expected_number_of_rows_for_last_report:int = total_number_of_rows % self.max_rows_per_report

        logger.info(f"Total number of rows: {total_number_of_rows}")
        logger.info(f"Max rows per report: {self.max_rows_per_report}")
        logger.info(f"Expected number of reports to be generated: {expected_number_of_reports_to_be_generated}")
        logger.info(f'Expected number of rows for last report: {expected_number_of_rows_for_last_report}')

        for rule in self.rules:
            if not rule.is_enabled:
                logger.info(f"Skipping rule {rule.name} because is not enabled")
                continue
            
            if len(rule.rows) == 0:
                logger.info(f"Skipping rule {rule.name} because it contains no rows")
                continue
            
            logger.info(f"Exporting rows for rule {rule.name}")
            logger.debug(f"Number of rows for rule: {len(rule.rows)}")

            extractors:str = rule.get_all_extractors_for_html_report(extractor_template)
            row_hidden:str = "hidden" if self.hide_rows_automatically else ""
            for row in sorted(set(rule.rows)):
                hostname:str = urlparse(row.strip()).netloc
                if hostname:
                    # split(":")[0] -> remove port from hostname
                    hostnames.append(hostname.split(":")[0])
                rows.append(row_template\
                            .replace("@@FULL_URL", row.strip())\
                            .replace("@@ROW_HIDDEN", row_hidden))
                
                report_row_counter += 1
                total_row_counter += 1
                if report_row_counter == self.max_rows_per_report:
                    # Close the panel and create the report
                    # Create the report because the max num. of rows has been reached
                    logger.debug(f"Report #{report_counter}: Close the panel and create the report. Max num rows per report ({self.max_rows_per_report}) has been reached. Row counter: {report_row_counter}")
                    panels.append(panel_template \
                        .replace("@@RULE_NAME", rule.name) \
                        .replace("@@EXTRACTORS", extractors) \
                        .replace("@@ROWS", "\n".join(rows)))
                    self.__save_report(output_directory, panels, \
                                        self.__get_report_name(report_base_filename, report_counter, expected_number_of_reports_to_be_generated), \
                                        self.__get_report_pages(report_base_filename, expected_number_of_reports_to_be_generated, report_counter), \
                                        hostnames)
                    report_row_counter = 0
                    panels = []
                    rows = []
                    hostnames = []
                    report_counter += 1
                    pass
            
            # Close the panel if there are rows for the panel (row_counter > 0)
            if report_row_counter > 0:
                logger.debug(f"Report #{report_counter}: Close the panel because there are rows left for the panel. Row counter: {report_row_counter}")
                panels.append(panel_template \
                    .replace("@@RULE_NAME", rule.name) \
                    .replace("@@EXTRACTORS", extractors) \
                    .replace("@@ROWS", "\n".join(rows)))
                rows = []

        # Create the report if there are rows left (row_counter > 0)
        if report_row_counter > 0:
            logger.debug(f"Report #{report_counter}: Create the report because there are rows left for the report. Row counter: {report_row_counter}")
            self.__save_report(output_directory, panels, \
                                self.__get_report_name(report_base_filename, report_counter, expected_number_of_reports_to_be_generated), \
                                self.__get_report_pages(report_base_filename, expected_number_of_reports_to_be_generated, report_counter), \
                                hostnames)

        logger.debug(f"Total row counter: {total_row_counter} | Total number of rows: {total_number_of_rows}")

    # region HTML Report
    def __get_report_name(self, report_base_filename:str, report_counter:int, total_number_of_reports:int):
        return f'{report_base_filename}_{format(report_counter, f'0{len(str(total_number_of_reports))}')}.html'
    
    def __get_report_pages(self, report_base_filename:str, total_number_of_reports:int, current_report_number:int) -> list[str]:
        page_template:str = self.__load_page_template()
        pages:list[str] = []
        for i in range(0, total_number_of_reports):
            report_filename:str = self.__get_report_name(report_base_filename, i, total_number_of_reports)
            selected:str = "selected" if current_report_number == i else ""
            pages.append(page_template \
                        .replace("@@SELECTED", selected) \
                        .replace("@@REPORT_FILENAME", report_filename)
                        .replace("@@REPORT_NUMBER", str(i)))
        return pages

    def __save_report(self, output_directory:str, panels:list[str], report_filename:str, pages:list[str], hostnames:list[str]):
        if not panels:
            return
        
        selected_display_rows:str = "" if self.hide_rows_automatically else "selected"
        selected_hide_rows:str = "selected" if self.hide_rows_automatically else ""

        hostname_select_template:str = self.__load_hostname_select_template()
        hostnames = sorted(set(hostnames))
        for i in range(0, len(hostnames)):
            hostnames[i] = hostname_select_template.replace("@@HOSTNAME", hostnames[i])

        base_template:str = self.__load_base_template()
        output:str = base_template \
            .replace("@@PANELS", "\n".join(panels)) \
            .replace("@@PAGES", "\n".join(pages)) \
            .replace("@@SELECTED_DISPLAY_ROWS", selected_display_rows) \
            .replace("@@SELECTED_HIDE_ROWS", selected_hide_rows) \
            .replace("@@HOSTNAMES", "\n".join(hostnames))

        logger.info(f"Saving report {report_filename}")
        with open(f'{output_directory}/{report_filename}', "w") as output_file:
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
    def __load_page_template(self) -> str:
        with open(f"{CrawlingReport.TEMPLATE_DIRECTORY}/page_template.html", "r") as page_template:
            return page_template.read()
    def __load_hostname_select_template(self) -> str:
        with open(f"{CrawlingReport.TEMPLATE_DIRECTORY}/hostname_select_template.html", "r") as hostname_select_template:
            return hostname_select_template.read()
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
            crawling_report.create_html_reports(OUTPUT_DIRECTORY)
            logger.info("Report created successfully!")
        else:
            print_help()

    except Exception as excp:
        logger.exception(excp)

if __name__ == '__main__':
    main()