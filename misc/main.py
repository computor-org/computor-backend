from enum import Enum
import os
#from computor_backend.interface.course_content_types import CTutorUIColor
from misc.icons_template import TestedType, icon_assignment_template, icon_unit_template

class CTutorUIColor(str, Enum):
    RED = 'red'
    ORANGE = 'orange'
    AMBER = 'amber'
    YELLOW = 'yellow'
    LIME = 'lime'
    GREEN = 'green'
    EMERALD = 'emerald'
    TEAL = 'teal'
    CYAN = 'cyan'
    SKY = 'sky'
    BLUE = 'blue'
    INDIGO = 'indigo'
    VIOLET = 'violet'
    PURPLE = 'purple'
    FUCHSIA = 'fuchsia'
    PINK = 'pink'
    ROSE = 'rose'

color_mapping = {
    CTutorUIColor.RED: {'htmlColor': '#FF0000', 'cross': '#FFFFFF', 'check': '#32CD10'},
    CTutorUIColor.ORANGE: {'htmlColor': '#FFA500', 'cross': '#FFFFFF', 'check': '#FFFFFF'},
    CTutorUIColor.AMBER: {'htmlColor': '#FFBF00', 'cross': '#FF0000', 'check': '#32CD10'},
    CTutorUIColor.YELLOW: {'htmlColor': '#FFFF00', 'cross': '#FF0000', 'check': '#32CD10'},
    CTutorUIColor.LIME: {'htmlColor': '#00FF00', 'cross': '#FF0000', 'check': '#FFFFFF'},
    CTutorUIColor.GREEN: {'htmlColor': '#0ec40e', 'cross': '#FF0000', 'check': '#FFFFFF'},
    CTutorUIColor.EMERALD: {'htmlColor': '#50C878', 'cross': '#FF0000', 'check': '#FFFFFF'},
    CTutorUIColor.TEAL: {'htmlColor': '#008080', 'cross': '#FFFFFF', 'check': '#FFFFFF'},
    CTutorUIColor.CYAN: {'htmlColor': '#00FFFF', 'cross': '#FF0000', 'check': '#000000'},
    CTutorUIColor.SKY: {'htmlColor': '#87CEEB', 'cross': '#FF0000', 'check': '#32CD10'},
    CTutorUIColor.BLUE: {'htmlColor': '#0000FF', 'cross': '#FFFFFF', 'check': '#32CD10'},
    CTutorUIColor.INDIGO: {'htmlColor': '#4B0082', 'cross': '#FF0000', 'check': '#32CD10'},
    CTutorUIColor.VIOLET: {'htmlColor': '#EE82EE', 'cross': '#FFFFFF', 'check': '#FFFFFF'},
    CTutorUIColor.PURPLE: {'htmlColor': '#800080', 'cross': '#FFFFFF', 'check': '#32CD10'},
    CTutorUIColor.FUCHSIA: {'htmlColor': '#FF00FF', 'cross': '#FFFFFF', 'check': '#FFFFFF'},
    CTutorUIColor.PINK: {'htmlColor': '#FFC0CB', 'cross': '#FFFFFF', 'check': '#32CD10'},
    CTutorUIColor.ROSE: {'htmlColor': '#FF007F', 'cross': '#FFFFFF', 'check': '#32CD10'},
}

def create_assignments(base_dir):

    base_dir = os.path.join(base_dir,"assignments")

    if not os.path.exists(base_dir):
        os.makedirs(base_dir,exist_ok=True)

    for theme in ["light","dark"]:

        for test_type in TestedType:

            for key in color_mapping.keys():

                value = color_mapping[key]
                color = value['htmlColor']
                cross = value['cross']
                check = value['check']

                ic_dir = os.path.join(base_dir,theme,test_type)
                if not os.path.exists(ic_dir):
                    os.makedirs(ic_dir,exist_ok=True)

                with open(os.path.join(ic_dir,f"{key}.svg"),"w") as file:
                    theme_border_color = "black"

                    if theme == "light":
                        theme_border_color = 'black'
                    elif theme == "dark":
                        theme_border_color = 'white'

                    icon_template = icon_assignment_template(color,theme_border_color,cross,check,test_type)
                
                    file.write(icon_template)

def create_units(base_dir):
    base_dir = os.path.join(base_dir,"units")

    if not os.path.exists(base_dir):
        os.makedirs(base_dir,exist_ok=True)

    for theme in ["light","dark"]:
        ic_dir = os.path.join(base_dir,theme)

        for key in color_mapping.keys():
            value = color_mapping[key]
            color = value['htmlColor']
            
            if not os.path.exists(ic_dir):
                os.makedirs(ic_dir,exist_ok=True)

            with open(os.path.join(ic_dir,f"{key}.svg"),"w") as file:
                theme_border_color = "black"

                icon_template = icon_unit_template(color,theme)

                file.write(icon_template)


if __name__ == "__main__":

    base_dir = "resources/icons"

    create_assignments(base_dir)
    create_units(base_dir)