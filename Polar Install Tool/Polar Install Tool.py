# Script for downloading all csv files from airfoiltools.com for later analysis
# written by Max Pollard 2022 maxpollardii@gmail.com for use by UTD DBF
import os
import requests
import re
import bs4
from tkinter import Tk, Button, Label
from tkinter.filedialog import askdirectory, askopenfilename


# Tkinter class that handles the prompting of the csv directory and the airfoil name list
class PromptFileGui:
    def __init__(self, master, prompt_type):
        self.prompt_return = None
        self.master = master
        self.master.title("Airfoil Scoring Tool")
        if prompt_type == "directory":
            self.text_prompt = Label(master=self.master,
                                     text="Please select the directory where the csv files should be stored")
            self.text_prompt.pack()

            self.choose_directory_button = Button(master=self.master, text="Choose Directory",
                                                  command=self.prompt_directory)
            self.choose_directory_button.pack()
        elif prompt_type == "file":
            self.text_prompt = Label(master=self.master,
                                     text="Please select the file where the list of airfoils is stored\n"
                                          "Format should be a .txt file with one airfoil per line in \n"
                                          "either link format or the name listed on airfoil tools that ends in -il\n"
                                          "If you did not mean to select this, just close this window")
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


# I'm not sure why all of these are invalid escape sequences, but they work and pass all the tests I used so
# this should be fine
# URL for page with all airfoils linked
ALL_AIRFOILS_PAGE = "http://airfoiltools.com/search/airfoils"

# regex for finding the href for the csv file download
CSV_FILE_REGEX = re.compile("(?<=href=\")(\S*\.csv)")

# regex for extracting the name of the airfoil from the download link for csv
AIRFOIL_NAME_CSV_REGEX = re.compile("((?<=polar=)(\S*?)(?=-il-))")

# regex for extracting name of airfoil from airfoil link
AIRFOIL_NAME_LINK_REGEX = re.compile("((?<=airfoil=)\S*)")

# regex for extracting max thickness from the airfoil website
AIRFOIL_MAX_THICKNESS_REGEX = re.compile("((?<=thickness )[\d.]+?(?=%))")

# regex for extracting max camber from the airfoil website
AIRFOIL_MAX_CAMBER_REGEX = re.compile("((?<=camber )[\d.]+?(?=%))")


def get_airfoil_links():
    # creates a list of the links for all airfoils listed on the main page in the following format
    # http://airfoiltools.com/airfoil/details?airfoil=airfoil_name
    # create response object
    all_airfoils_response = requests.get(ALL_AIRFOILS_PAGE)

    # create beautiful-soup object with lxml parser
    all_airfoil_soup = bs4.BeautifulSoup(all_airfoils_response.content, "html.parser")

    # find all link elements on web-page
    link_elements = all_airfoil_soup.findAll('a')

    # For each link in the list (i.e. has a tag of 'a') that ends with -il, adds an element to
    # the list airfoil_links_list with the format root url + href portion
    airfoil_links_list = [("http://airfoiltools.com" + link.get('href'))
                          for link in link_elements if link['href'].endswith('il')]
    # print(airfoil_links_list)
    return airfoil_links_list


def get_max_thickness_camber(airfoil_link, session):
    try:
        airfoil_page_text = str(session.get(airfoil_link).text)
        airfoil_max_thickness = AIRFOIL_MAX_THICKNESS_REGEX.search(airfoil_page_text).group()
        airfoil_max_camber = AIRFOIL_MAX_CAMBER_REGEX.search(airfoil_page_text).group()
    except requests.exceptions.RequestException:
        print("Airfoil at %s could not be downloaded" % airfoil_link)
        return None

    return [airfoil_max_thickness, airfoil_max_camber]


def download_csv_files(all_airfoil_links, target_directory, parameters):
    download_session = requests.Session()
    # Writes a file of all airfoil links for which polar csv's should be downloaded for future reference
    all_airfoil_links_file = open(target_directory + '\\airfoils_links.txt', "w")
    for airfoil_link in all_airfoil_links:
        all_airfoil_links_file.write(airfoil_link + '\n')
    all_airfoil_links_file.close()

    # Running list of all links that failed to be downloaded for whatever reason to be retried at the end of execution
    failed_download_links = []
    failed_download_file = open(target_directory + '\\failed_download_links.txt', "w")

    # creates a list of formattable strings for the names and links of csv files
    # (one for each combination of Reynolds value and nCrit)
    csv_link_formats = []
    file_name_formats = []
    file_name = ''  # in case of error, this should be defined to be something

    for value in [50000, 100000, 200000, 500000, 1000000]:
        # Parameters list is in format [nCrit Value, min Reynolds Value, max Reynolds value]
        # checks each possible reynolds value for which the website has data, if it's within search parameters, adds an
        # entry to the possible formats using this reynolds value and the correct nCrit value

        if parameters[1] <= value <= parameters[2]:
            if parameters[0] == 5 or parameters[0] == 0:
                csv_link_formats.append("http://airfoiltools.com/polar/csv?polar=xf-{name}-" +
                                        str(value) + "-n5\">xf-{name}-" + str(value) + "-n5.csv")
                file_name_formats.append(target_directory + '\\' + "{name}" + '_R_' + str(value) + '_N_' + str(5) +
                                         '.csv')
            if parameters[0] == 9 or parameters[0] == 0:
                csv_link_formats.append("http://airfoiltools.com/polar/csv?polar=xf-{name}-" +
                                        str(value) + "\">xf-{name}-" + str(value) + ".csv")
                file_name_formats.append(target_directory + '\\' + "{name}" + '_R_' + str(value) + '_N_' + str(9) +
                                         '.csv')

    # For each link in the list, downloads a csv for each format in the csv_link_formats list
    for airfoil_link in all_airfoil_links:
        # Parses airfoil link to find airfoil name
        airfoil_name = AIRFOIL_NAME_LINK_REGEX.search(airfoil_link).group()

        thickness_camber_list = get_max_thickness_camber(airfoil_link, download_session)
        if thickness_camber_list is None:
            # This is a fail condition
            for csv_link_format in csv_link_formats:
                failed_download_file.write(csv_link_format.format(name=airfoil_name) + '\n')
            continue

        thickness_string_insert = f"Max Thickness,{thickness_camber_list[0]}\nMax Camber,{thickness_camber_list[1]}\n"

        # Counter for which index of the file_name_format list should be used (the for statement iterates through the
        # csv_link_formats so a separate counter is used

        file_name_format_index = 0
        for link_format in csv_link_formats:
            # for each formattable string pair,
            # downloads the csv at the formatted link, naming it the formatted name

            # Flag for whether the download at this link was successful
            failure = False
            csv_link = link_format.format(name=airfoil_name)

            try:
                csv_request = download_session.get(csv_link)

                if not csv_request.status_code == 200:
                    # This means that this something went wrong (usually means there isn't a csv file for this combo)
                    print("Status code: %s\t" % str(csv_request.status_code))
                    failure = True
                # print(csv_link)
                # print(file_name)
                if not failure:
                    # Edits response to add the camber and thickness to the csv
                    csv_request_split = csv_request.text.split("Url")
                    csv_edited = csv_request_split[0] + thickness_string_insert + csv_request_split[1]

                    file_name = file_name_formats[file_name_format_index].format(name=airfoil_name)
                    csv_file = open(file_name, "w")
                    csv_file.write(csv_edited)
                    csv_file.close()

            except requests.exceptions.RequestException as e:
                print(str(e) + "\n")
                failure = True
            except PermissionError:
                print("Permission error\nPlease close %s to be able to edit this file" % file_name)
            if failure:
                print("Failed to download %s\n" % csv_link)
                failed_download_links.append(csv_link)
                failed_download_file.write(csv_link + '\n')

            file_name_format_index += 1

    failed_download_file.close()
    # print("Failed downloads: ")
    # print(failed_download_links)


def download_csv_link_list(target_directory, csv_link_list):
    download_session = requests.Session()
    # Given a list of csv_links, will download them
    for csv_link in csv_link_list:
        airfoil_name = AIRFOIL_NAME_CSV_REGEX.search(csv_link).group()
        if csv_link[-6:-4] == 'n5':
            n_crit_value = 5
            reynolds_number = int(csv_link[-14:-7].strip('il-'))
        else:
            n_crit_value = 9
            reynolds_number = int(csv_link[-11:-4].strip('il-'))
        # print(reynolds_number)
        # print(n_crit_value)

        csv_content = download_session.get(csv_link).content
        file_name = f'{target_directory}\\{airfoil_name}_R_{str(reynolds_number)}_N_{str(n_crit_value)}.csv'
        open(file_name, "wb").write(csv_content)
    return


def prompt_n_crit():
    # request the nCrit value that should be downloaded
    while True:
        # loops until a valid nCrit value is entered
        try:
            n_crit_entered = int(
                input("Please enter the nCrit value to be downloaded, either \"5\", \"9\", or \"0\" for both\n"))
            # Checks if nCrit is a value for which there are files on this site to download
            if not ((n_crit_entered == 5) or (n_crit_entered == 9) or (n_crit_entered == 0)):
                print('There are no files available for this n_crit_entered value, please try 5, 9, or 0')
                continue

        except ValueError:
            print('Please enter an integer')
        else:
            break
    return n_crit_entered


def prompt_reynolds_num():
    # prompts user for reynolds number, asks for min, then max
    valid_range_entered = False
    reynolds_min = 0
    reynolds_max = 0
    while not valid_range_entered:
        try:
            reynolds_min = int(input("Please enter minimum reynolds value to be downloaded\n"))
            reynolds_max = int(input("Please enter maximum reynolds value to be downloaded\n"))
        except ValueError:
            print("Please enter an integer")
            continue
        for num in [50000, 100000, 200000, 500000, 1000000]:
            if reynolds_min <= num <= reynolds_max:
                valid_range_entered = True
                break
        if not valid_range_entered:
            print(
                "There is no data for the reynolds values in this range, there is data for 50000, 100000, 200000, "
                "500000, and 1000000")
    return [reynolds_min, reynolds_max]


def prompt_y_n(prompt):
    while True:
        response = input(prompt).lower().replace(" ", "")
        if response == "y" or response == "yes":
            return True
        elif response == 'n' or response == "no":
            return False
        else:
            print("Please enter yes or no")


def prompt_file(prompt):
    # Asks user for a file, loops until a file that exists is inputted
    while True:
        file_name = input(prompt)
        if os.path.isfile(file_name):
            return file_name
        else:
            print("This file appears to not exist, please try again hombre\n")


def parse_airfoils_from_list(file_path):
    # Given a file that contains a list of name of airfoils separated by new lines(either containing or missing -il)
    # will return a list of links of the airfoils
    airfoil_file = open(file_path, "r")
    link_format_string = "http://airfoiltools.com/airfoil/details?airfoil={airfoil_name}"

    # If the line is just a name with -il, formats it using the format string (minus the \n character)
    # If the line is a name without -il, adds it then formats
    # If the line is already a link, just strips the \n character
    airfoil_link_list = [line.strip("\n") if line[0:4] == 'http'
                         else link_format_string.format(airfoil_name=(line.strip("\n")))
                         if line[-4:] == '-il\n'
                         else link_format_string.format(airfoil_name=(line.strip('\n') + '-il'))
                         for line in airfoil_file]
    return airfoil_link_list


if __name__ == "__main__":
    # Creates a tkinter gui to prompt a directory
    root = Tk()
    prompt_directory_gui = PromptFileGui(root, "directory")
    root.mainloop()
    directory_path = prompt_directory_gui.prompt_return
    root.destroy()

    # input the directory in which the airfoil polar files, airfoil links, and downloaded csvs should be downloaded
    # print("Please choose the directory to which the csv files should be saved\n")
    # directory_path = askdirectory()

    # prompts to see if there is a file of the airfoils that should be downloaded
    airfoil_links = None
    airfoil_list_exists = prompt_y_n("Have you made a list of airfoils that should be downloaded?\n"
                                     "Please enter Y or N\n")
    if airfoil_list_exists:
        while True:
            root = Tk()
            prompt_norm_file_gui = PromptFileGui(root, "file")
            root.mainloop()
            airfoil_list_file_name = prompt_norm_file_gui.prompt_return
            if airfoil_list_file_name is None:
                # This means they exited out before choosing a file
                break
            root.destroy()

            try:
                airfoil_links = parse_airfoils_from_list(airfoil_list_file_name)
                break
            except PermissionError:
                print("This file could not be opened, please close it and select this or another list\n")

    # prompts for parameters for downloaded files
    n_crit = prompt_n_crit()
    reynolds_range = prompt_reynolds_num()
    search_parameters = [n_crit, reynolds_range[0], reynolds_range[1]]

    # create the list of links of the airfoils if one wasn't explicitly given
    if airfoil_links is None:
        airfoil_links = get_airfoil_links()

    print("List of %d airfoil links created\n" % len(airfoil_links))
    print("Beginning download, please leave this running undisturbed, the longest this\n"
          "process has ran for me is about two hours, but your mileage may vary\n"
          "depending on computer specs/network connection, etc.\n")

    # downloads a list of all csv links matching parameters, creates list of all airfoil links, creates list of all
    # downloaded csv files
    download_csv_files(airfoil_links, directory_path, search_parameters)

    print("Download Complete")
    input("Press enter to close")

# Everything after this is just code chunks I removed but would be very sad to delete because they took bloody forever
# to write, please ignore

# Because the files are all in the same format, this is wholly unnecessary
'''
def generate_csv_regex(parameters):
    # generates a compiled regex to find links for desired data ranges
    # parameters[0] = nCrit value, [1] is min reynolds, [2] is max reynolds
    r_portion = ""  # r_portion is a list of all reynolds values we want data about, separated by | for use in a regex
    for num in [50000, 100000, 200000, 500000, 1000000]:
        if parameters[1] <= num <= parameters[2]:
            r_portion += f'{num}|'

    # removes the extra | from the end of the expression
    r_portion = r_portion[:-1]

    # creates a string referring to the group that handles checking the reynolds value
    n_portion = ''  # This is case nCrit = 9
    if parameters[0] == 5:
        n_portion = '-n5'
    elif parameters[0] == 0:
        n_portion = '-n5|'

    group = f"(?<=href=\")([\S]*(?:{r_portion})(?:{n_portion}))(?=\")"
    regex_tag = re.compile(group, re.IGNORECASE)
    return regex_tag
'''

# The following code actually searches through the html response from each airfoil link and finds the csv that way,
# which is a cool proof of concept, but is VERY slow and because they're all in the same format, I'm not sure why I
# thought that this was necessary
'''
# given a regex tag that finds all csv files with the given parameters, a list of links to various airfoils, and a
# target directory, saves every csv file to the directory with the format airfoil_name_R_ReynoldsNumber_N_nCritValue
# If this is used later, make sure to add the regex tag parameter
for airfoil_link in all_airfoil_links:
    # print(airfoil_link)

    airfoil_response = requests.get(airfoil_link)
    airfoil_content = str(airfoil_response.content)

    # print(str(airfoil_response.airfoil_content))

    # Parses airfoil link to find airfoil name
    airfoil_name = AIRFOIL_NAME_LINK_REGEX.search(airfoil_link).group()
    # print(airfoil_name)

    all_polar_links = csv_regex_tag.findall(airfoil_content)  # links to all polar pages with correct parameters
    for polar_link in all_polar_links:
        # finds the download link for the csv file on the polar page, downloads the file
        print(polar_link)
        if polar_link[-2:] == 'n5':
            n_crit_value = 5
            reynolds_number = int(polar_link[-10:-3].strip('il-'))
        else:
            n_crit_value = 9
            reynolds_number = int(polar_link[-7:].strip('il-'))
        # print(reynolds_number)
        # print(n_crit_value)

        csv_response = requests.get("http://airfoiltools.com" + polar_link)
        csv_link = "http://airfoiltools.com" + CSV_FILE_REGEX.search(str(csv_response.content)).group()
        csv_request = requests.get(csv_link).content
        file_name = target_directory + '\\' + airfoil_name + '_R_' + str(reynolds_number) + '_N_' + \
                    str(n_crit_value) + '.csv'
        open(file_name, "wb").write(csv_request)

        # Adds this link to the file of downloaded files
        all_downloaded_polar_links.write(csv_link + '\n')
    all_downloaded_airfoil_links.write(airfoil_link + '\n')
all_downloaded_polar_links.close()
all_downloaded_airfoil_links.close()
'''

'''
    # This functionality is mostly pointless so has been removed
    # prompts to see if there is a list of csv links to be downloaded (tbd)
    file_tbd_name = prompt_file("csv link list")
    # If there is a file of links, downloads these and exits
    if file_tbd_name is not None:
        file_tbd = open(file_tbd_name, "r")
        csv_link_list = [line.strip('\n') for line in file_tbd]
        print(csv_link_list)
        download_csv_link_list(directory_path, csv_link_list)
        exit()
    '''
'''
# prompts to see if there is an airfoil to start with (in case of a mid-download failure)
valid_response = False
while not valid_response:
    start_pt_exists = input(
        "Is there a airfoil link to begin with? (In the case that a download failed midway, enter the name of "
        "the first airfoil in the failed_download_links.txt file)\nPlease enter Y/N\n")

    if start_pt_exists == 'Y' or start_pt_exists == 'y':
        start_pt = input("Please enter the full link to the airfoil to start at\n")
        # finds the index of the starting point within the airfoil_links list
        try:
            starting_index = airfoil_links.index(start_pt)
            if starting_index > 0:
                del airfoil_links[0:starting_index-1]
                valid_response = True
            elif starting_index == 0:
                valid_response = True
            else:
                print(".index returned a negative number which is kinda wack, try that again pls")
        except ValueError:
            print("This link was not found in the airfoil list")
    elif start_pt_exists == 'N' or start_pt_exists == 'n':
        valid_response = True
    else:
        print("Please enter Y or N")
'''
