# Script for scoring airfoils using csv generated using the sister tool, polar download tool
# Written by Max Pollard 2022 maxpollardii@gmail.com for use by UTD DBF club
import os
import regex
import sys
from tkinter import Label, Button, Tk
from tkinter.filedialog import askdirectory, askopenfilename
import requests
from bs4 import BeautifulSoup

# Global dictionary for storing the index corresponding to each data type as it is stored in the CsvData alpha_value
# dictionary
value_index_dict = {
    "alpha": 0,
    "cl": 1,
    "cd": 2,
    "cp": 3,
    "cm": 4,
    "top_xtr": 5,
    "bot_xtr": 6
}

config_template_string = "# Configuration settings for csv scoring analysis\n" \
"# Absolute file path to the directory where the csv files are stored (In quotation marks)\n" \
"# For example, csv_directory_path = \"C:\\Users\\maxpo\\Desktop\\csv edited folder\"\n" \
"csv_directory_path= \"{csv_directory_path}\"\n" \
"# absolute file path to where the csv file of the airfoil to which the others should be normed is stored\n" \
"# For example, norm_file = \"C:\\Users\\maxpo\\Desktop\\csv edited folder\\clarky_R_50000_N_9.csv\"\n" \
"norm_file_path = \"{norm_file_path}\"\n\n" \
"# For Ncrit_Num, use 5 for 5, 9 for 9, and 0 for both (No data available for other values)\n" \
"Ncrit_Num = {nCrit_num}\n\n" \
"# Data is available for Reynolds Numbers 50,000, 100,000, 200,000, 500,000, and 1,000,000 " \
"# (Range should encompass at least one of these)\n" \
"Reynolds_Min = {reynolds_min}\n" \
"Reynolds_Max = {reynolds_max}\n\n" \
"# Thickness is the maximum thickness of the airfoil as found on Airfoiltools.com listed as a percentage\n" \
"Thickness_Min = {thickness_min}%\n" \
"Thickness_Max = {thickness_max}%\n\n" \
"# Max Camber is the maximum camber of the airfoil as found on Airfoiltools.com listed as a percentage\n" \
"Camber_Min = {camber_min}%\n" \
"Camber_Max = {camber_max}%\n\n" \
"# For a hopefully thorough explanation of how to construct and format a scoring equation, please see the README.txt\n"\
"Scoring_Equation = {scoring_equation}\n"

# Regex for extracting the name, reynolds num, ncrit num, etc. from csv file name
AIRFOIL_NAME_CSV_REGEX = regex.compile(r"((?<=/)(\S*?)(?=_R_))")
REYNOLDS_NUM_REGEX = regex.compile(r"((?<=_R_)(\S*?)(?=_N_))")
N_CRIT_NUM_REGEX = regex.compile(r"((?<=_N_)(\S*?)(?=.csv))")

# Regex for extracting airfoil name from download link
# AIRFOIL_NAME_LINK_REGEX = regex.compile("((?<=polar=)(\S*?)(?=-il-))")

# regex for extracting max thickness, camber from the csv itself
AIRFOIL_MAX_THICKNESS_REGEX = regex.compile(r"((?<=Thickness,)[\d.]+?(?=\n))")
AIRFOIL_MAX_CAMBER_REGEX = regex.compile(r"((?<=Camber,)[\d.]+?(?=\n))")


# Regexes for extracting settings from the config file
CONFIG_CSV_DIRECTORY_REGEX = regex.compile(r"((?<=\ncsv_directory_path *= *\")[^\n]*(?=\" *\n))", regex.IGNORECASE)
CONFIG_NORM_FILE_REGEX = regex.compile(r"((?<=\nnorm_file_path *= *\")[^\n]*(?=\" *\n))", regex.IGNORECASE)
CONFIG_NCRIT_NUM_REGEX = regex.compile(r"((?<=\nNcrit_Num *= *)[^\n]*(?= *\n))", regex.IGNORECASE)
CONFIG_REYNOLDS_MIN_REGEX = regex.compile(r"((?<=\nreynolds_min *= *)[\d]*(?= *\n))", regex.IGNORECASE)
CONFIG_REYNOLDS_MAX_REGEX = regex.compile(r"((?<=\nreynolds_max *= *)[\d]*(?= *\n))", regex.IGNORECASE)
CONFIG_THICKNESS_MIN_REGEX = regex.compile(r"((?<=\nthickness_min *= *)[\d.]*(?= *%? *\n))", regex.IGNORECASE)
CONFIG_THICKNESS_MAX_REGEX = regex.compile(r"((?<=\nthickness_max *= *)[\d.]*(?= *%? *\n))", regex.IGNORECASE)
CONFIG_CAMBER_MIN_REGEX = regex.compile(r"((?<=\ncamber_min *= )[\d.]*(?= *%? *\n))", regex.IGNORECASE)
CONFIG_CAMBER_MAX_REGEX = regex.compile(r"((?<=\ncamber_max *= )[\d.]*(?= *%? *\n))", regex.IGNORECASE)
CONFIG_EQUATION_STRING_REGEX = regex.compile("((?<=\nscoring_equation *= *)[^\n]*(?=$|\n))", regex.IGNORECASE)


# Exception for when the equation can't be evaluated for whatever reason
class UnableToEvaluate(Exception):
    pass


# Tkinter class that handles the prompting of the csv directory and the norming file
class PromptFileGui:
    def __init__(self, master, prompt_type):
        self.prompt_return = None
        self.master = master
        self.master.title("Airfoil Scoring Tool")
        if prompt_type == "directory":
            self.text_prompt = Label(master=self.master,
                                     text="Please select the directory where the csv files are stored\n")
            self.text_prompt.pack()

            self.choose_directory_button = Button(master=self.master, text="Choose Directory",
                                                  command=self.prompt_directory)
            self.choose_directory_button.pack()
        elif prompt_type == "file":
            self.text_prompt = Label(master=self.master,
                                     text="Please select the csv file to which the other csv files should be normed")
            self.text_prompt.pack()

            self.choose_file_button = Button(master=self.master, text="Choose File",
                                             command=self.prompt_file)
            self.choose_file_button.pack()

    def prompt_directory(self):
        self.prompt_return = askdirectory()
        self.master.quit()

    def prompt_file(self):
        self.prompt_return = askopenfilename()
        self.master.quit()


# Class for storing an Airfoil
class Airfoil:
    def __init__(self, name, file_path):
        self.airfoil_details_link = f"http://airfoiltools.com/airfoil/details?airfoil={name}"
        self.description = None
        self.score = None
        self.name = name
        self.file_path = file_path
        if file_path is not None:
            self.csv_data = CsvData(file_path)

    def __str__(self):
        if self.description is None:
            self.find_description()
        return "Name: {name}\tDescription: {description}\t" \
               "Score {score}\t File Path: {file_path}".format(name=self.name, description=self.description,
                                                                score=self.score, file_path=self.file_path)

    def __repr__(self):
        if self.description is None:
            self.find_description()
        return "Name: {name}\tDescription: {description}\t" \
               "Score {score}\t File Path: {file_path}".format(name=self.name, description=self.description,
                                                               score=self.score, file_path=self.file_path)

    def score_airfoil(self, parsed_equation_string, normed_airfoil_data):
        self.score = self.csv_data.score_csv(parsed_equation_string, normed_airfoil_data)

    def find_description(self):
        try:
            airfoil_description_soup = BeautifulSoup(requests.get(self.airfoil_details_link).content, "html.parser")
            airfoil_description_class = airfoil_description_soup.find("td", {'class': 'cell1'})
            if airfoil_description_class is None:
                print(f"No airfoil description class found for {self.name}")
            else:
                try:
                    self.description = (str(airfoil_description_class).split('<br/>')[1])
                except IndexError:
                    print("No Description found in airfoil description class")
        except requests.exceptions.RequestException:
            print(f"Description could not be parsed from airfoil {self.name}")


# Class for parsing and storing the values of an airfoil simulation
class CsvData:
    def __init__(self, csv_file_path):
        self.csv_file_path = csv_file_path
        self.parse_values_return = self.parse_values()
        self.alpha_value_dict = self.parse_values_return[1]
        self.alpha_list = self.parse_values_return[0]
        self.max_Cl_Cd = self.parse_values_return[2]
        self.max_Cl_Cd_Alpha = self.parse_values_return[3]

    def parse_values(self):
        # Opens the scv, returns the tasty goodies
        csv_file = open(self.csv_file_path, "r")

        # List of every angle of attack for which this airfoil has data
        alpha_list = []

        # Dictionary with the key being the angle of attack and the value being a list of all values
        # (angle of attack, Cl, etc)
        alpha_value_dict = {}

        # Starts at the 14th line (The original download starts at 12 but the polar download tool I made adds
        # Max thickness and camber so new beginning is 14)
        current_line_index = 13

        all_lines = csv_file.readlines()
        num_lines = len(all_lines)

        if all_lines[0][0:12] != "Xfoil polar.":
            # This means that this is not an airfoil data file in the format for which this script is written
            raise IndexError

        max_Cl_Cd = all_lines[6].split(',')[1]
        max_Cl_Cd_Alpha = all_lines[7].split(',')[1]

        while current_line_index < num_lines:
            line_tokens = regex.split(r',', all_lines[current_line_index])
            try:
                alpha_value_dict[float(line_tokens[0])] = tuple((float(line_tokens[index]) for index in range(0, 7)))
                alpha_list.append(float(line_tokens[0]))

            except ValueError:
                print(f"Error reading line {current_line_index} in {self.csv_file_path}")
            current_line_index += 1

        csv_file.close()
        return [alpha_list, alpha_value_dict, max_Cl_Cd, max_Cl_Cd_Alpha]

    def find_stall_angle(self):
        # Iterates through the angles of attack, finds first angle of attack where the Cl is lower than the last
        # If a stall angle is negative, probably a sailplane airfoil lmao
        previous_Cl = self.alpha_value_dict[self.alpha_list[0]][1]

        for angle in self.alpha_list:
            current_Cl = (self.alpha_value_dict[angle])[1]
            if previous_Cl > current_Cl > 0:
                return angle
            previous_Cl = current_Cl
        print(f"No stall angle could be found for airfoil at {self.csv_file_path} so the maximum angle of attack for \n"
              f"which there is data was used instead")
        return self.alpha_list[-1]

    def alpha_norm_tuple(self, norm_csv_data):
        # Makes a new list of angles of attack that are shared between this airfoil and the
        # norming airfoil for a fair comparison (same value dict can be used... yay dictionaries)
        alpha_tuple_normed = (angle for angle in norm_csv_data.alpha_list if angle in self.alpha_list)
        return alpha_tuple_normed

    def score_csv(self, parsed_equation_string, normed_airfoil_data):
        try:
            return eval(parsed_equation_string)
        except Exception as e:
            print("CSV could not be scored\nError Output:")
            print(repr(e))
            return None

    def find_data_list(self, data_index, alpha_values):
        # Returns a list with each element being the value at index "data_index" of the tuple that is the value pair of
        # the key of an element in alpha_values
        # For example, if this is passed 1 in data_index, it will return every Coefficient of lift for this data set, 2
        # will return the coefficients of drag, etc
        data_list = [self.alpha_value_dict[alpha_value][data_index] for alpha_value in alpha_values]
        return data_list


# Class for handling the configuration settings of this program
class ConfigSettings:
    def __init__(self):
        self.csv_directory_path = None
        self.norm_file_path = None
        self.nCrit_num = None
        self.reynolds_min = None
        self.reynolds_max = None
        self.thickness_min = None
        self.thickness_max = None
        self.camber_min = None
        self.camber_max = None
        self.scoring_equation = None

    def parse_config_file(self):
        # Reads the config file, stores everything in the places that they should go, returns errors on fail
        parse_succeed_flag = True
        try:
            # Because this isn't really a proper application, when this executes, it is relegated to a temporary
            # file where the config file is stored, this returns path to the executable
            cwd = os.path.abspath(os.path.dirname(sys.executable))

            with open(os.path.join(cwd, "analysis_settings.config"), "r") as config_file:
                config_file_text = config_file.read()
                config_file.close()
                csv_directory_match = CONFIG_CSV_DIRECTORY_REGEX.search(config_file_text)
                if csv_directory_match is not None:
                    self.csv_directory_path = csv_directory_match.group()
                else:
                    print("Csv Directory could not be parsed (Make sure that the file path is enclosed in quotes)")
                    parse_succeed_flag = False

                norm_file_path_match = CONFIG_NORM_FILE_REGEX.search(config_file_text)
                if norm_file_path_match is not None:
                    self.norm_file_path = norm_file_path_match.group()
                else:
                    print("Norm File Path could not be parsed(Make sure that the file path is enclosed in quotes")
                    parse_succeed_flag = False

                nCrit_num_match = CONFIG_NCRIT_NUM_REGEX.search(config_file_text)
                if nCrit_num_match is not None:
                    try:
                        self.nCrit_num = int(nCrit_num_match.group())
                    except ValueError:
                        print("Invalid Value passed to nCrit number")
                        parse_succeed_flag = False
                else:
                    print("Ncrit number could not be parsed")
                    parse_succeed_flag = False

                reynolds_min_match = CONFIG_REYNOLDS_MIN_REGEX.search(config_file_text)
                if reynolds_min_match is not None:
                    try:
                        self.reynolds_min = int(reynolds_min_match.group())
                    except ValueError:
                        print("Invalid Value passed to reynolds minimum")
                        parse_succeed_flag = False
                else:
                    print("Minimum Reynolds Value could not be parsed")
                    parse_succeed_flag = False

                reynolds_max_match = CONFIG_REYNOLDS_MAX_REGEX.search(config_file_text)
                if reynolds_max_match is not None:
                    try:
                        self.reynolds_max = int(reynolds_max_match.group())
                    except ValueError:
                        print("Invalid Value passed to reynolds maximum")
                        parse_succeed_flag = False
                else:
                    print("Maximum Reynolds Value could not be parsed")
                    parse_succeed_flag = False

                thickness_min_match = CONFIG_THICKNESS_MIN_REGEX.search(config_file_text)
                if thickness_min_match is not None:
                    try:
                        self.thickness_min = float(thickness_min_match.group())
                    except ValueError:
                        print("Invalid value passed to thickness_min")
                        parse_succeed_flag = False
                else:
                    print("Minimum Thickness Value could not be parsed")
                    parse_succeed_flag = False

                thickness_max_match = CONFIG_THICKNESS_MAX_REGEX.search(config_file_text)
                if thickness_max_match is not None:
                    try:
                        self.thickness_max = float(thickness_max_match.group())
                    except ValueError:
                        print("Invalid value passed to thickness_max")
                        parse_succeed_flag = False
                else:
                    print("Maximum Thickness Value could not be parsed")
                    parse_succeed_flag = False

                camber_min_match = CONFIG_CAMBER_MIN_REGEX.search(config_file_text)
                if camber_min_match is not None:
                    try:
                        self.camber_min = float(camber_min_match.group())
                    except ValueError:
                        print("Invalid value passed to camber_min")
                        parse_succeed_flag = False
                else:
                    print("Minimum Camber Value could not be parsed")
                    parse_succeed_flag = False

                camber_max_match = CONFIG_CAMBER_MAX_REGEX.search(config_file_text)
                if camber_max_match is not None:
                    try:
                        self.camber_max = float(camber_max_match.group())
                    except ValueError:
                        print("Invalid value passed to camber_max")
                        parse_succeed_flag = False
                else:
                    print("Maximum Camber Value could not be parsed")
                    parse_succeed_flag = False

                scoring_equation_match = CONFIG_EQUATION_STRING_REGEX.search(config_file_text)
                if scoring_equation_match is not None:
                    self.scoring_equation = scoring_equation_match.group()
                else:
                    print("Scoring equation count not be parsed")
                    parse_succeed_flag = False
        except IOError:
            print("Config file could not be opened")
            parse_succeed_flag = False
        return parse_succeed_flag

    def input_config_settings(self):
        # Prompts the user for config settings and stores them to object
        # Creates a tkinter gui to prompt a directory choice for csv file choice
        root = Tk()
        prompt_directory_gui = PromptFileGui(root, "directory")
        root.attributes("-topmost", True)
        root.mainloop()
        self.csv_directory_path = prompt_directory_gui.prompt_return
        root.destroy()

        # Creates a tkinter gui to prompt the user to enter an airfoil to norm this one to
        root = Tk()
        prompt_norm_file_gui = PromptFileGui(root, "file")
        root.attributes("-topmost", True)
        root.mainloop()
        self.norm_file_path = prompt_norm_file_gui.prompt_return
        root.destroy()

        # Request parameters for airfoils that should be considered
        self.nCrit_num = input_integer("Please enter the nCrit number for airfoil results that should be used,"
                                       " 5 for 5, 9 for 9, or 0 for both.\n", [5, 9, 0], True)
        while True:
            self.reynolds_min = input_integer(
                "Please enter the minimum value for the Reynolds number of simulations that will "
                "be analyzed\nCsv files have data on Reynolds Numbers 50,000, 100,000, 200,000, "
                "500,000 and 1,000,000\n")
            self.reynolds_max = input_integer(
                "Please enter the maximum value for the Reynolds number of simulations that will "
                "be analyzed\n")
            if self.reynolds_max >= self.reynolds_min:
                break
            else:
                print("Reynolds min greater than Reynolds max, please enter valid bounds.")

        # Inputs thickness range
        while True:
            self.thickness_min = input_float(
                "Please enter the minimum value for the airfoil's maximum thickness that should be "
                "considered\n")
            self.thickness_max = input_float(
                "Please enter the maximum value for the airfoil's maximum thickness that should be "
                "considered\n")
            if self.thickness_max >= self.thickness_min:
                break
            else:
                print("Thickness min greater than thickness max, Please enter valid bounds.\n")

        # Inputs Camber Range
        while True:
            self.camber_min = input_float("Please enter the minimum value for the airfoil's "
                                          "maximum camber that should be considered\n")
            self.camber_max = input_float("Please enter the maximum value for the airfoil's "
                                          "maximum camber that should be considered\n")
            if self.camber_max >= self.camber_min:
                break
            else:
                print("Camber min greater than camber max. Please enter valid bounds.\n")
            # Request an equation for the scoring
        self.scoring_equation = input(
            "Please enter the equation used to calculate the score for each airfoil.\n"
            "For a list of usable operators, values, etc, please check the README.txt\n")

    def is_valid(self):
        # validates the current config settings(won't validate the equation)
        valid_flag = True
        if not os.path.isfile(self.norm_file_path):
            print("Invalid norm file path given")
            valid_flag = False
        if not os.path.isdir(self.csv_directory_path):
            print("Invalid csv directory given")
            valid_flag = False
        if self.nCrit_num not in [0, 9, 5]:
            print("Ncrit number passed for which no simulation data is available")
            valid_flag = False
        reynolds_numbers_in_range = 0
        for reynolds_num in [50000, 100000, 200000, 500000, 1000000]:
            if self.reynolds_min <= reynolds_num <= self.reynolds_max:
                reynolds_numbers_in_range += 1
        if reynolds_numbers_in_range == 0:
            print("Range of Reynolds numbers values passed does not contain any of the values for which simulation\n"
                  "data is available: 50,000 100,000, 200,000, 500,000, or 1,000,000")
            valid_flag = False
        if self.thickness_min > self.thickness_max:
            print("Thickness maximum smaller than thickness minimum")
            valid_flag = False
        if self.camber_min > self.camber_max:
            print("Camber maximum small than camber minimum")
            valid_flag = False
        return valid_flag

    def write(self):
        # Writes the config file to the analysis_settings.config file
        # Opens the template, copies the template to a formattable string, formats it wil all current config settings
        # values, writes the formatted string to the config settings file
        config_file_format_string = config_template_string
        config_file_string = config_file_format_string.format(csv_directory_path=self.csv_directory_path,
                                                              norm_file_path=self.norm_file_path,
                                                              nCrit_num=self.nCrit_num,
                                                              reynolds_min=self.reynolds_min,
                                                              reynolds_max=self.reynolds_max,
                                                              thickness_min=self.thickness_min,
                                                              thickness_max=self.thickness_max,
                                                              camber_min=self.camber_min,
                                                              camber_max=self.camber_max,
                                                              scoring_equation=self.scoring_equation)

        cwd = os.path.abspath(os.path.dirname(sys.executable))
        with open(os.path.join(cwd, "analysis_settings.config"), "w") as config_file:
            config_file.write(config_file_string)
            config_file.close()

    def __repr__(self):
        # string representation of this object for printing configuration settings at beginning of program execution
        return f"directory path: \"{self.csv_directory_path}\"\nnorm_file_path: {self.norm_file_path}\nNcrit num: " \
               f"{self.nCrit_num}\nReynolds number between {self.reynolds_min}, {self.reynolds_max}\n" \
               f"Max thickness percentage between {self.thickness_min}% and {self.thickness_max}%\nMax Camber between "\
               f"{self.camber_min}% and {self.camber_max}%\nScoring Equation= {self.scoring_equation}\n"


# Makes a dictionary of each pair of parentheses
def find_parens(s):
    p_loc_dict = {}
    pstack = []

    for index, character in enumerate(s):
        if character == '(':
            pstack.append(index)
        elif character == ')':
            if len(pstack) == 0:
                raise IndexError("No matching closing parens at: " + str(index))
            p_loc_dict[pstack.pop()] = index

    if len(pstack) > 0:
        raise IndexError("No matching opening parens at: " + str(pstack.pop()))

    return p_loc_dict


# Parses the string into something that can be evaluated using eval()
def process_equation_string(given_equation_string, csv_data_object):
    # standardizes the string so spaces and capitalization don't matter
    processed_string = given_equation_string
    processed_string = processed_string.replace(" ", "")
    processed_string = processed_string.lower()

    # Replaces parameters that have already been calculated with the csv object members, so they don't need to be
    # recalculated (more efficient yay)
    processed_string = processed_string.replace("stall_angle", "self.find_stall_angle()")
    processed_string = processed_string.replace("max(element_wise_operation(cl,cd,/))", "self.max_Cl_Cd")
    processed_string = processed_string.replace("alpha(maxclcd)", "self.max_Cl_Cd_Alpha")

    # replaces the name of the parameter with the method that the csv data object uses to find it
    for value_type in ["alpha", "cl", "cd", "cp", "cm", "top_xtr", "bot_xtr"]:
        processed_string = processed_string.replace(value_type, f"self.find_data_list({value_index_dict[value_type]}, "
                                                                f"self.alpha_list)")

    # replaces all the normed parameters with an expression that divides the
    while "norm(" in processed_string:
        # dictionary that contains key value pairs of the beginning parenthesis and the corresponding ending one
        paren_loc_dict = find_parens(processed_string)
        norm_begin_index = processed_string.index("norm(")
        string_to_be_normed = processed_string[norm_begin_index + 5: paren_loc_dict[norm_begin_index + 4]]

        # Because the parsing behaviour should be different depending on whether the string to be normed returns list or
        # a value, this determines what it will return (self is defined as a csv_data_object so when eval is called on
        # the equation string it can be evaluated and the return type of the equation can be determined)
        self = csv_data_object
        string_return_type_is_list = isinstance(eval(string_to_be_normed), list)

        # the same string as the string_to_be_normed, but will use data from the norming airfoil instead
        norm_value_string = string_to_be_normed.replace("self", "normed_airfoil_data")

        # If the normed string returns a list, the two lists should contain values for the same angles of attack (i.e.
        # only contain comparable values
        if string_return_type_is_list:
            string_to_be_normed = string_to_be_normed.replace("alpha_list", "alpha_norm_tuple(normed_airfoil_data)")
            norm_value_string = norm_value_string.replace("normed_airfoil_data.alpha_list",
                                                          "self.alpha_norm_tuple(normed_airfoil_data)")
        replacement_string = f"element_wise_operation({string_to_be_normed}, {norm_value_string}, \"/\""

        # slices out the norm(expression) and replaces it with the replacement string
        processed_string = processed_string[0:norm_begin_index] + \
                           replacement_string + \
                           processed_string[paren_loc_dict[norm_begin_index + 4]:]

    return processed_string


# Handles prompting the user for a float
def input_float(prompt_string, range_bounds=None):
    while True:
        try:
            return_float = float(input(prompt_string))
            if range_bounds is None or range_bounds[0] <= return_float <= range_bounds[1]:
                return return_float
        except ValueError:
            print("Please enter a float")


# Handles prompting the user for an integer
def input_integer(prompt_string, value_set=None, limited=False):
    # if value_set is none, any integer is allowed, if limited is false, value set is a min max, if limited is true,
    # then value_set is the only allowable values that can be entered
    if value_set is not None and not limited and len(value_set) != 2:
        print("Input_integer was passed a value set of length not 2 and limited = false")
        return None

    while True:
        try:
            return_int = int(input(prompt_string))
            if value_set is None or \
                    (limited and return_int in value_set) or \
                    (not limited and value_set[0] <= return_int <= value_set[1]):
                return return_int
            else:
                print("Please enter one of the following values " + ",".join(str(element) for element in value_set)
                      if limited
                      else f"Please enter an integer between {value_set[0]} and {value_set[1]}")
        except ValueError:
            print("Please enter an integer")


# Handles prompting for bool values
def input_y_n(prompt):
    while True:
        response = input(prompt).lower().replace(" ", "")
        if response == "y" or response == "yes":
            return True
        elif response == 'n' or response == "no":
            return False
        else:
            print("Please enter yes or no")


def average(value_list):
    if isinstance(value_list, float) or isinstance(value_list, int):
        value_list = [value_list]

    # returns the average value of a list
    running_sum = 0.0
    element_count = 0
    for value in value_list:
        running_sum += value
        element_count += 1
    return running_sum / element_count


# Performs the same operation to every value in a list (adds a constant, subtracts, etc)
def list_value_operation(given_list, value, operator):
    try:
        value = float(value)
    except ValueError:
        print("Invalid Value passed to list_value_operation as parameter 2, should be an integer or float\n")
        raise UnableToEvaluate

    if isinstance(given_list, list):
        if operator == "+":
            return_list = [list_value + value for list_value in given_list]
        elif operator == "-":
            return_list = [list_value - value for list_value in given_list]
        elif operator == "*":
            return_list = [list_value * value for list_value in given_list]
        elif operator == "/":
            return_list = [list_value / value for list_value in given_list]
        elif operator == "^":
            return_list = [pow(list_value, value) for list_value in given_list]
        else:
            print("Operator passed to list_value_operation not recognized")
            raise UnableToEvaluate
    else:
        print("Non-list passed to list_value_operation as parameter 1")
        raise UnableToEvaluate
    return return_list


# Performs an operation between corresponding elements of equal length lists ([1,2,3], [4,5,6], "+") = [5,7,9], etc
def element_wise_operation(parameter_one, parameter_two, operator):
    # If parameter one and two are both ints/floats, converts them both to lists of length
    # one so the program logic still works
    if (isinstance(parameter_one, float) or isinstance(parameter_one, int)) and \
            (isinstance(parameter_two, float) or isinstance(parameter_two, int)):
        parameter_one = [parameter_one]
        parameter_two = [parameter_two]
    if isinstance(parameter_one, list) and isinstance(parameter_two, list):
        if len(parameter_one) != len(parameter_two):
            raise UnableToEvaluate(
                "Lists of unequal length passed to element_wise_operation, Operation cannot be performed")
        list_length = len(parameter_one)

        if operator == "+":
            return_list = [parameter_one[index] + parameter_two[index] for index in range(0, list_length)]
        elif operator == "-":
            return_list = [parameter_one[index] - parameter_two[index] for index in range(0, list_length)]
        elif operator == "*":
            return_list = [parameter_one[index] * parameter_two[index] for index in range(0, list_length)]
        elif operator == "/":
            try:
                return_list = [parameter_one[index] / parameter_two[index] for index in range(0, list_length)]
            except ZeroDivisionError:
                raise UnableToEvaluate("Value in divisor list passed to element_wise_operation contains 0, division by "
                                       "zero cannot\nbe accomplished")
        elif operator == "^":
            return_list = [pow(parameter_one[index], parameter_two[index]) for index in range(0, list_length)]
        else:
            raise UnableToEvaluate("Operator passed to list_value_operation not recognized")
    else:
        raise UnableToEvaluate(
            f"{type(parameter_one)} and {type(parameter_two)} passed to element_wise_operation. Please fix scoring "
            f"equation")

    # If its only one value, should be returned as such (shouldn't cause problems, but we shall see)
    if len(return_list) == 1:
        return return_list[0]
    return return_list


# Makes a list of all csv files that should be scored as they match whatever parameters were given
def find_airfoil_csvs(config_settings):
    all_file_names = os.listdir(config_settings.csv_directory_path)
    csv_file_names = []
    # For each file in this directory, checks if it is a CSV File of an airfoil with test parameters in range
    for file_name in all_file_names:
        if file_name[-4:] != '.csv':
            continue

        # Tries to parse reynolds and ncrit numbers from the file name
        # On fail, this is the wrong type of csv file
        try:
            r_num_current = int(REYNOLDS_NUM_REGEX.search(file_name).group())
            n_crit_current = int(N_CRIT_NUM_REGEX.search(file_name).group())
        except AttributeError:
            continue

        # If the n_crit number matches the parameters passed and the reynolds number is within range, parses the
        # max thickness and camber values from the csv file and if those are also within range, adds this csv file
        # to the list, otherwise, continues
        if not ((config_settings.reynolds_min <= r_num_current <= config_settings.reynolds_max) and
                (config_settings.nCrit_num == 0 or n_crit_current == config_settings.nCrit_num)):
            continue

        # Opens and reads the file to parse thickness and camber values from it
        csv_file_data = open(config_settings.csv_directory_path + '/' + file_name).readlines()
        try:
            csv_max_thickness = float(csv_file_data[8].split(',')[1])
            csv_max_camber = float(csv_file_data[9].split(',')[1])
        except ValueError:
            print("Error parsing max thickness or max camber for %s\n" % file_name)
            continue

        # this is a way of doing it with a regex, they seem to be the same speed so either works
        '''
        try:
            csv_max_thickness = float(AIRFOIL_MAX_THICKNESS_REGEX.search(csv_file_data).group())
            csv_max_camber = float(AIRFOIL_MAX_CAMBER_REGEX.search(csv_file_data).group())
        except (ValueError, AttributeError):
            print("Unreadable Thickness or Camber value for %s\n" % file_name)
            continue
        '''
        if config_settings.thickness_min <= csv_max_thickness <= config_settings.thickness_max and \
                config_settings.camber_min <= csv_max_camber <= config_settings.camber_max:
            csv_file_names.append(config_settings.csv_directory_path + '/' + file_name)
    return csv_file_names


# evaluates every airfoil, returns the 5 best scorers
def find_best(csv_file_paths, given_equation_string, norm_file_path):
    score_array = []
    norm_airfoil_data = CsvData(norm_file_path)

    # Running list of the best airfoils so far in order from best to worse
    airfoil_best_running = []

    # Parses the given equation string into something that can be evaluated
    parsed_equation_string = process_equation_string(given_equation_string, norm_airfoil_data)


    print(parsed_equation_string)
    for file_path in csv_file_paths:
        # Creates an Airfoil Data Class to store the values from this csv
        current_airfoil = Airfoil(AIRFOIL_NAME_CSV_REGEX.search(file_path).group(), file_path)
        current_airfoil.score_airfoil(parsed_equation_string, norm_airfoil_data)
        current_score = current_airfoil.score
        score_array.append(current_score)
        if current_score is None:
            print("No score could be calculated for:")
            print(current_airfoil)
            continue

        # Index that this value will replace if it's lower than all
        # subsequent scores (If 5, it is lower than all scores)
        replace_index = len(airfoil_best_running)
        while replace_index > 0:
            # Checks if it beats the score that's one higher than it on the list
            if (airfoil_best_running[replace_index - 1].score is None
                    or current_score > airfoil_best_running[replace_index - 1].score):
                # If this is higher than the score that has an index of one lower, lowers index that this airfoil
                # should replace
                replace_index -= 1
            else:
                break

        airfoil_best_running.insert(replace_index, current_airfoil)

    return airfoil_best_running


# Replaces an item in a list at a given index with some new value, pushes everything back one, removes the last element
def replace_item(given_list, index_to_replace, item_to_insert):
    shifted_list = given_list
    current_index = index_to_replace
    temp_storage_one = item_to_insert

    while current_index < len(given_list):
        temp_storage_two = shifted_list[current_index]
        shifted_list[current_index] = temp_storage_one
        temp_storage_one = temp_storage_two
        current_index += 1
    return shifted_list


def display_airfoil_scores(ordered_airfoil_list):
    place = 1
    for airfoil in ordered_airfoil_list:
        print(str(place)+". "+str(airfoil))
        place += 1


if __name__ == "__main__":
    mainConfig = ConfigSettings()
    config_configured = input_y_n("Have you configured the analysis_settings.config to match your preferences?\n"
                                  "Please enter yes if you have and would like to use these settings and no if\n"
                                  "you have not (If not, the program will prompt you for those parameters now\n"
                                  "and set up the analysis_settings.config with these parameters for use next time)\n")

    if not config_configured:
        mainConfig.input_config_settings()
        mainConfig.write()
    else:
        parse_succeeded = mainConfig.parse_config_file()
        if not parse_succeeded or not mainConfig.is_valid():
            print("Config file is not usable, beginning config setup")
            mainConfig.input_config_settings()
            mainConfig.write()

    print("Configuration Settings to be used:")
    print(mainConfig)

    # Creates a list of all csv files that should be considered given parameters
    print("Finding list of airfoils within parameters to use(can take a while depending on parameters)")
    file_paths = find_airfoil_csvs(mainConfig)

    print(f"List of {len(file_paths)} csv files for consideration created, beginning analysis")
    print("This should be relatively quick(under 10 min)")
    # Output the top 5 scores with associated polar file names
    best_airfoil_list = find_best(file_paths, mainConfig.scoring_equation, mainConfig.norm_file_path)
    display_airfoil_scores(best_airfoil_list[0:5])
    airfoil_to_remove_place = input_integer("Please enter the placing of any airfoil you would like to remove from "
                                            "consideration\nI.E enter 1 for the first place, 5 for the 5th place, "
                                            "etc\nTo remove none, enter 0\n", [0, 1, 2, 3, 4, 5], True)
    # Displays the scores and lets the user remove some of them from consideration
    while airfoil_to_remove_place != 0:
        best_airfoil_list.pop(airfoil_to_remove_place - 1)
        display_airfoil_scores(best_airfoil_list[0:5])
        airfoil_to_remove_place = input_integer("Please enter the placing of any airfoil you would like to remove from "
                                                "consideration\nI.E enter 1 for the first place, 5 for the 5th place, "
                                                "etc\nTo remove none, enter 0\n", [0, 1, 2, 3, 4, 5], True)
    input("Press enter to exit")


'''
#Finds all lists that need to be parsed from csv before evaluating the expression (This wasn't used because it felt
# much more complex than just parsing everything)
def find_necessary_lists(equation_string):
    necessary_lists_return = []
    for list_name in ["Alpha", "Cl", "Cd", "Cp", "Cm"]:
        if equation_string.find(list_name) != -1:
            necessary_lists_return.append(list_name)

    # Dictionary pairing the name of the lists to their index in the necessary_lists return list
    necessary_lists_dict = {necessary_lists_return[num]: num for num in range(0, len(necessary_lists_return))}
    return [necessary_lists_return, necessary_lists_dict]
'''
