This is a test to see if we can run a python web app locally, similarly to how it is done in the toolkit wrapper.

# Prerequisites
1. You will need git installed on your machine. This can be downloaded from the Software Centre
2. You will need to have python >=3.12 installed on your machine. This can be downloaded from the Software Centre
3. You will need to have pip installed on your machine. https://pip.pypa.io/en/stable/installation/

# Instructions

1. Clone this repo using 
```
git clone https://github.com/kenbannon/flask-poetry.git
```   
<br>

2. Navigate to the repo in your terminal by running
```
cd flask-poetry
```
<br>

3. Install the package by navigating to where the repo is located and running 
```
python -m pip install .
```

You may not have the command `python` on your path if installed from the Software Centre. If this is the case, you can try this command instead:
```
py -m pip install .
```
<br>

4. Run the app by running this command. You may need to restart your command prompt to get the flask command to work after previous step.
```
python -m flask --app flask_poetry\example\run-the-app run
```
You may not have the command `python` on your path if installed from the Software Centre. If this is the case, you can try these commands instead for steps:
```
py -m flask --app flask_poetry\example\run-the-app run
```
<br>

# Troubleshooting
You may not have the command `python` or `py` on your PATH. If this is the case then you will need to investigate where your python installation is located and use the full path to the python executable. You can find the location of your python installation by running the following command in your terminal:
```
where python
```
or
```
which python
```
This will return the location of the python executable. You can then use this location to run the commands in the instructions above. For example, if the location of the python executable is `C:\Users\user\AppData\Local\Programs\Python\Python310\python.exe` then you would run the following command to install the package:
```
C:\Users\user\AppData\Local\Programs\Python\Python310\python.exe -m pip install .
```
and the following command to run the app:
```
C:\Users\user\AppData\Local\Programs\Python\Python310\python.exe -m flask --app flask_poetry\example\run-the-app run
```

