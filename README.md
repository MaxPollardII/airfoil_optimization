# airfoil_optimization
Airfoil Optimization Choice Tool READ_ME.md

Written by Max Pollard 2022 maxpollardii@gmail.com 

This is a pair of python executables used to aid in the choice of an airfoil based on CFD simulations of the behaviour of the airfoil at different angles of attack.

Instructions:
Polar Install Tool:
Follow prompts, enter search parameters, and be prepared to wait a while (the server it is downloading the csv's from is pretty slow)
If you are worried it isn't working, check the folder into which the csv files should be downloaded. If this is being populated, all is good. An error 404 message usually implies that the simulation data does not exist for this combination of parameters and is usually not an issue.


IN CASE OF PROGRAM CRASH MID_DOWNLOAD (hasn't happened to me yet but I'm pretty bad at error handling)
Go into the directory where the csv files were being loaded into, find the file airfoil_links.txt, remove the links for every successful download (The files are downloaded in the same order as this list so find the airfoil of the last successful download and delete everything before that one) and select the edited airfoil_links.txt file when prompted if you have made a list of airfoils to be downloaded. This will prevent wasting time by redownloading these.

IF THERE IS A LIMITED SET OF AIRFOILS YOU WANT TO DOWNLOAD
Write a .txt file with each line being the name of an airfoil you want to download data about (the name should be the one ending in -il) or the link to the details page of this airfoil(This link looks like http://airfoiltools.com/airfoil/details?airfoil=ag16-il). When prompted asking if you have a list of airfoils you want to download, enter yes and select this file


Instructions:
SCORING_ANALYSIS.py:
The second script is for evaluating a given equation on each set of airfoil data and returning a list of the best performers.

If this is the first time you are using this script on a particular machine or you wish to change any settings from last time, please enter no when asked "Have you configured the analysis_settings.config to match your preferences?"
Then follow the prompts to enter parameters, wait for it to finish analysis, et voila. If any of these are airfoils that you don't like (they are a windmill airfoil, etc), just enter what place they scored when prompted to remove them and display the new list of the best 5. (For example, to delete the best scorer, enter 1, and to delete the 5th best, enter 5)

Note: These csv's are edited by the polar install tool to contain max thickness and camber, analysis won't work with csv files downloaded straight from the website


How to write a scoring equation string
Types of expressions:
To return the values for any of the following, simply enter one of the following terms
alpha, cl, cd, cp, cm, top_xtr, bot_xtr, stall_angle

alpha is angle of attack, cl is coefficient of lift, cd is coefficient of drag, cp is coefficient of parasitic drag, cm is coefficient of moment, top_xtr is the position on the top of the airfoil that laminar airflow becomes turbulent, bot_xtr is the same on the bottom of the airfoil, stall angle is the stall angle
Please note that all of these values with the exception of stall angle are lists and a value must be extracted from these to be useful. 

To extract useful information from these, max(list_name), min(list_name), average(list_name) will return the maximum, minimum, and average of the lists, respectively 

For example, if all that is important is maximum coefficient of lift, the scoring equation you would use is max(cl)

If you want ratios between these values, for example the ratio of lift to parasitic drag, use the function element_wise_operation(list1, list2, operator (this must be in quotes))
element_wise_operation performs the operation between each corresponding element of the two lists and returns the result
For example, if list_1 is [1,2,3] and list_2 is [4,1,2], and the operator is '*', the result of 
element_wise_operation(list_1, list_2, "*") would be [4, 2, 6]

Note: The operator parameter must be in quotes, i.e. "+", "-", "*", "/", "^" or it will not be evaluated
For the previous example of the ratio of coefficient of lift to coefficient of parasitic drag, the expression would read
element_wise_operation(cl, cp, "/")
This would return a list, where every value is the coefficient of lift divided by the coefficient of parasitic drag at the same angle of attack. If you want to turn this list into a score, use max, min, average, etc.

Value Operators
+, -, *, /, pow(value, power) These are operators that do exactly what you would expect(Please note that these work on values, ie Max(Cl), not lists (ie Cl))
Please note that anything that can be evaluated in python can be used in this equation. Please use this with care as I have not done much error checking on this type of operation.

Norming:
norm(expression) This will evaluate "expression" for both the airfoil currently being scored and the airfoil that was chosen as the norming airfoil (usually the clarky-il airfoil) It will then divide the two, returning the result. This can be done on both lists (i.e. cl) or values(i.e. max(cl)) 
For example, if you want the score to equal the maximum coefficient of moment of the current airfoil divided by the maximum coefficient of moment for the norming airfoil, enter norm(max(cm))

Examples:
max(cl)
.4 * norm(max(cl)) -.3 * norm(max(cd))+.2*norm(min(element_wise_operation(cp,cd,'/')))+.1*norm(max(cm))
norm(max(cl))



