from fpdf import FPDF, XPos, YPos
import textwrap
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import base64
from fastapi.staticfiles import StaticFiles
from io import BytesIO
from PIL import Image
import math


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PatientReport(FPDF):
    def __init__(self, json_data):
        """
        Initialize report with JSON data containing all information
        json_data: JSON string or dict containing all report data
        """
        super().__init__()
        self.set_auto_page_break(auto=True, margin=30)
        
        # Parse JSON if string is provided
        if isinstance(json_data, str):
            self.data = json.loads(json_data)
        else:
            self.data = json_data
            
        # Store all sections of data
        self.patient_data = self.data.get('patient_data', {})
        self.hospital_data = self.data.get('hospital_data', {})
        self.doctor_data = self.data.get('doctor_data', {})
        self.advice_data = self.data.get('advice_data', [])
        self.previous_reports = self.data.get('previous_reports', [])
        
        # Store logo data
        self.logo_data = self.data.get('logo_data', "logo.jpg")
        self.watermark_logo = self.data.get('watermark_logo', "logo.jpg")
        
        # Define colors for the report (teal/green theme)
        self.primary_color = (0, 128, 128)  # Teal
        self.secondary_color = (0, 150, 136)  # Green teal
        self.accent_color = (0, 77, 64)  # Dark teal
        self.light_accent = (224, 242, 241)  # Very light teal
        self.light_grey = (192, 192, 192)  # Light Grey
        self.generated_watermark = self.create_watermark_image()

        

    def create_watermark_image(self):
        """Generates a watermark image from the watermark_logo."""
        if not hasattr(self, 'watermark_logo') or not self.watermark_logo:
            return None

        try:
            img = Image.open(self.watermark_logo).convert("L").convert("RGBA")
            watermark = Image.new("RGBA", img.size, (255, 255, 255, 0))
            watermark.paste(img, (0, 0), img)
            pixels = watermark.load()
            for y in range(watermark.size[1]):
                for x in range(watermark.size[0]):
                    r, g, b, a = pixels[x, y]
                    pixels[x, y] = (r, g, b, 60)  # Adjust opacity here
            
            # Save to BytesIO object
            watermark_bytes = BytesIO()
            watermark.save(watermark_bytes, format="PNG")
            watermark_bytes.seek(0)
            return watermark_bytes

        except Exception as e:
            print(f"Error creating watermark: {e}")
            return None

    def create_table(self, table_data, title='', data_size=10, title_size=12, 
                     align_data='C', align_header='L', cell_width='even', 
                     x_start='x_default', emphasize_data=[], emphasize_style=None, 
                     emphasize_color=(0, 0, 0)):
        default_style = self.font_style
        if emphasize_style is None:
            emphasize_style = default_style

        

        def get_col_widths():
            col_width = cell_width
            num_cols = 0  # Initialize num_cols
            if isinstance(table_data, list) and table_data:  # Check if list is not empty
                num_cols = len(table_data[0])
            elif isinstance(table_data, dict) and table_data:  # Check if dictionary is not empty
                num_cols = len(list(table_data.values())[0])

            if num_cols == 0:  # Handle empty table_data
                return 0  # Or return an appropriate default

            if col_width == 'even':
                col_width = self.epw / num_cols - 1 if num_cols > 0 else 0
            elif col_width == 'uneven':
                col_widths = []
                for col in range(num_cols):
                    longest = 0
                    if isinstance(table_data, list):
                        for row in table_data:
                            if col < len(row):  # Ensure col index is valid
                                cell_value = str(row[col])
                                value_length = self.get_string_width(cell_value)
                                char_limit = 30
                                num_lines = (len(cell_value) // char_limit) + 1
                                wrapped_length = value_length / num_lines
                                if wrapped_length > longest:
                                    longest = wrapped_length
                    else:  # Dictionary case
                        dict_values = list(table_data.values())
                        if dict_values and col < len(dict_values):
                            col_data = dict_values[col]
                            for row_index in range(len(col_data)):
                                cell_value = str(col_data[row_index])
                                value_length = self.get_string_width(cell_value)
                                char_limit = 30
                                num_lines = (len(cell_value) // char_limit) + 1
                                wrapped_length = value_length / num_lines
                                if wrapped_length > longest:
                                    longest = wrapped_length
                    col_widths.append(longest + 4)
                col_width = col_widths
            elif isinstance(col_width, list):
                col_width = col_width
            else:
                try:
                    col_width = int(col_width)
                except ValueError:
                    col_width = self.epw / num_cols - 1 if num_cols > 0 else 0
            return col_width

        if isinstance(table_data, dict):
            header = [key for key in table_data]
            data = []
            for key in table_data:
                value = table_data[key]
                data.append(value)
            data = [list(a) for a in zip(*data)]
        else:
            header = table_data[0]
            data = table_data[1:]

        line_height = self.font_size * 3

        col_width = get_col_widths()
        self.set_font(size=title_size)
            
        if x_start == 'C':
            table_width = 0
            if isinstance(col_width, list):
                for width in col_width:
                    table_width += width
            else:
                table_width = col_width * len(table_data[0])
            margin_width = self.w - table_width
            center_table = margin_width / 2
            x_start = center_table
            self.set_x(x_start)
        elif isinstance(x_start, int):
            self.set_x(x_start)
        elif x_start == 'x_default':
            x_start = self.set_x(self.l_margin)

        # TABLE CREATION #
        # Add title with primary color
        if title != '':
            self.set_text_color(*self.primary_color)
            self.multi_cell(0, line_height, title, border=0, align='j', ln=3, max_line_height=self.font_size)
            self.ln(line_height)
            self.set_text_color(0, 0, 0)  # Reset to black

        self.set_font(size=data_size)
        # Add header with teal background
        y1 = self.get_y()
        x_left = x_start if x_start != 'x_default' else self.l_margin
        if x_left is None:
            x_left = self.l_margin if self.l_margin is not None else 10
        x_right = self.epw + x_left if x_left is not None else self.epw + 10

        # Header with teal background
        self.set_fill_color(*self.primary_color)
        self.set_text_color(0, 0, 0)  # White text
        
        if isinstance(col_width, list):
            for i, datum in enumerate(header):  # Use header here
                adjusted_col_width = col_width[i]
                cell_value = str(datum)
                char_limit = 30  # Adjust as needed
                num_lines = (len(cell_value) // char_limit) + 1

                # Calculate cell height based on number of lines
                adjusted_line_height = line_height * num_lines

                self.multi_cell(adjusted_col_width, adjusted_line_height, datum, border=1, align=align_header,  # Border added
                                max_line_height=self.font_size, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True)
        else:
            for datum in header:  # Use header here
                cell_value = str(datum)
                char_limit = 30  # Adjust as needed
                num_lines = (len(cell_value) // char_limit) + 1

                # Calculate cell height based on number of lines
                adjusted_line_height = line_height * num_lines

                self.multi_cell(col_width, adjusted_line_height, datum, border=1, align=align_header,  # Border added
                                max_line_height=self.font_size, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True)
        self.ln(adjusted_line_height)

        # Alternating row colors
        row_counter = 0
        for row in data:
            x_left = x_start if x_start != 'x_default' else self.l_margin
            if x_left is None:
                x_left = self.l_margin if self.l_margin is not None else 10
            self.set_x(x_left)

            # Check for page break and set Y position
            if self.get_y() + line_height > self.h - self.b_margin:
                self.add_page()
                gap_height = 10  # Adjust this value for the desired gap size
                new_y = 50 + gap_height  # Add the gap to the initial Y-position
                self.set_y(new_y)
                self.set_x(x_left)

            # Alternating background for rows
            if row_counter % 2 == 0:
                self.set_fill_color(255, 255, 255)  # White
            else:
                self.set_fill_color(*self.light_accent)  # Very light teal

            row_counter += 1

            # Calculate max line height for the row
            max_row_height = 0
            if isinstance(col_width, list):
                for datum in row:
                    cell_value = str(datum)
                    char_limit = 30  # Adjust as needed
                    num_lines = (len(cell_value) // char_limit) + 1
                    adjusted_line_height = line_height * num_lines
                    max_row_height = max(max_row_height, adjusted_line_height)
            else:
                for datum in row:
                    cell_value = str(datum)
                    char_limit = 30  # Adjust as needed
                    num_lines = (len(cell_value) // char_limit) + 1
                    adjusted_line_height = line_height * num_lines
                    max_row_height = max(max_row_height, adjusted_line_height)

            if isinstance(col_width, list):
                for i, datum in enumerate(row):
                    adjusted_col_width = col_width[i]
                    self.multi_cell(adjusted_col_width, max_row_height, datum, border=1, align=align_data,  # Border added
                                    max_line_height=2 * self.font_size, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True)
            else:
                for datum in row:
                    self.multi_cell(col_width, max_row_height, datum, border=1, align=align_data,  # Border added
                                    max_line_height=2 * self.font_size, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True)
            self.ln(max_row_height) # Use max row height for consistent spacing.
            
        y3 = self.get_y()
        self.set_draw_color(*self.primary_color)  # Teal lines
        self.line(x_left, y3, x_right, y3)

    def add_watermark(self):
    # Save current position
        current_x, current_y = self.get_x(), self.get_y()
        x_position = self.w / 2
        y_position = self.h / 2
        logo_size = 60

        x_start = x_position - (logo_size / 2)
        y_start = y_position - (logo_size / 2)-30

        if self.generated_watermark:
            self.image(self.generated_watermark, x_start, y_start, logo_size)
        elif self.logo_data:
            self.image(self.logo_data, x_start, y_start, logo_size)

        self.set_xy(current_x, current_y)

    def header(self):
        margin = 10
        available_width = self.w - 2 * margin
        hospital_width = available_width * 0.5
        
        # Set background color for header section
        self.set_fill_color(255, 255, 255)
        self.rect(0, 0, self.w, 40, 'F')
        
        # Doctor Details with teal color
        self.set_y(10)
        self.set_font("helvetica", "B", 16)
        self.set_text_color(*self.primary_color)
        self.cell(0, 8, self.doctor_data.get('name', ''), 0, 1, "L")
        
        self.set_font("helvetica", "", 10)
        self.set_text_color(*self.secondary_color)
        self.cell(0, 5, self.doctor_data.get('degree', ''), 0, 1, "L")
        self.cell(0, 5, self.doctor_data.get('speciality', ''), 0, 1, "L")
        
        self.set_font("helvetica", "", 8)
        self.set_text_color(100, 100, 100)  # Gray text
        self.cell(0, 4, f"Mobile: {self.doctor_data.get('mobile', '')}", 0, 1, "L")
        self.cell(0, 4, f"PMC No. {self.doctor_data.get('pmc', '')}", 0, 1, "L")
        
        # Hospital Details
        self.set_y(10)
        self.set_x(self.w / 2)
        self.set_font("helvetica", "B", 16)
        self.set_text_color(*self.primary_color)
        self.cell(hospital_width, 8, self.hospital_data.get('name', ''), 0, 1, "R")
        
        self.set_font("helvetica", "I", 9)
        self.set_text_color(100, 100, 100)  # Gray slogan
        self.set_x(self.w / 2)
        # self.cell(hospital_width, 5, "SLOGAN HERE", 0, 1, "R")
        
        self.set_font("helvetica", "", 8)
        self.set_x(self.w / 2)
        self.cell(hospital_width, 4, self.hospital_data.get('address', ''), 0, 1, "R")
        self.set_x(self.w / 2)
        self.cell(hospital_width, 4, f"Tel: {self.hospital_data.get('phone', '')}", 0, 1, "R")
        self.set_x(self.w / 2)
        self.cell(hospital_width, 4, f"Emergency: {self.hospital_data.get('emergency', '')}", 0, 1, "R")
        
        # Divider line with primary color
        self.ln(5)
        self.set_draw_color(*self.primary_color)
        self.set_line_width(0.5)
        self.line(10, 40, self.w - 10, 40)
        self.set_line_width(0.2)
        self.ln(5)
        
        # Reset text color
        self.set_text_color(0, 0, 0)


    def footer(self):
        # Green footer bar
        self.set_fill_color(*self.primary_color)
        self.rect(0, self.h - 25, self.w, 25, 'F')
        
        # QR code section
        self.set_fill_color(255, 255, 255)
        self.rect(10, self.h - 25, 40, 25, 'F')
        
        # QR label
        self.set_xy(10, self.h - 20)
        self.set_font("helvetica", "B", 14)
        self.set_text_color(*self.primary_color)
        self.cell(40, 10, "QR", 0, 0, "C")
        
        # Footer text
        self.set_xy(60, self.h - 20)
        self.set_font("helvetica", "", 8)
        self.set_text_color(255, 255, 255)
        
        footer_data = self.hospital_data.get('footer', {})
        self.cell(0, 5, f"Address: {footer_data.get('address', '')}", 0, 1, "L")
        
        self.set_xy(60, self.h - 15)
        contact_line = f"Tel: {footer_data.get('phone', '')}   |   Email: {footer_data.get('email', '')}"
        self.cell(0, 5, contact_line, 0, 1, "L")
        
        # Page number on right side
        self.set_xy(self.w - 40, self.h - 15)
        self.cell(30, 5, "Page " + str(self.page_no()), 0, 0, "R")
    
    def previous_reports_header(self):
        margin = 10
        # Set green background for header
        self.set_fill_color(*self.primary_color)
        self.rect(0, 0, self.w, 40, 'F')
        
        # Add white text
        self.set_y(15)
        self.set_font("helvetica", "B", 18)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, "Previous Consultations", 0, 1, 'C')
        
        # Logo with white background
        if self.logo_data:
            self.set_fill_color(255, 255, 255)
            self.rect(margin, margin, 35, 35, 'F')
            self.image(self.logo_data, margin+2.5, margin+2.5, 30)
            
        # Return to make sure we know where the header ends
        return 50  # Return a fixed position after header

    def previous_reports_footer(self):
        # Similar to main report footer
        self.set_fill_color(*self.primary_color)
        self.rect(0, self.h - 15, self.w, 15, 'F')
        
        self.set_y(self.h - 12)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, "Page " + str(self.page_no()), 0, 0, "C")


class MainPatientReport(PatientReport):
    def generate_main_report(self, output_path=None):

        # print("Type of self.patient_data:", type(self.patient_data))
        # print("Contents of self.patient_data:", self.patient_data)
        # print("Age value:", self.patient_data.get('age'))
        # print("Date value:", self.patient_data.get('date'))

        """Generate report and return PDF as bytes"""
        self.add_page()
        self.add_watermark()  # Add the watermark

        # Patient information section with horizontal line at top
        self.set_draw_color(*self.primary_color)
        self.set_line_width(0.5)

        # Create patient info header section
        self.set_y(45)
        self.set_fill_color(*self.light_accent)
        self.rect(10, 45, self.w - 20, 20, 'F')  # Increased height to accommodate two lines

        # First line - Patient Name
        self.set_y(45)
        self.set_font("helvetica", "B", 10)
        self.set_text_color(*self.primary_color)
        self.set_x(10)

        # Calculate the width of "Patient Name:"
        patient_name_label = "Patient Name:"
        patient_name_label_width = self.get_string_width(patient_name_label) + 5  # Add some padding

        self.cell(patient_name_label_width, 10, patient_name_label, 0, 0, 'L')  # No new line

        # Add patient name value immediately after the header
        self.set_font("helvetica", "", 10)
        self.set_text_color(0, 0, 0)

        # Specify a width for the patient name cell
        patient_name_width = 80
        self.cell(patient_name_width, 10, self.patient_data.get('name', ''), 0, 1, 'L')  # Create new line

        age = self.patient_data.get('age','N/A')
        date = self.patient_data.get('date','N/A')
        
        # Second line headers - Age
        self.set_x(10)
        self.set_font("helvetica", "B", 10)
        self.set_text_color(*self.primary_color)

        # Age label
        age_label = "Age:"
        age_label_width = self.get_string_width(age_label) + 5
        self.cell(age_label_width, 10, age_label, 0, 0, 'L')

        # Age value
        self.set_font("helvetica", "", 10)
        self.set_text_color(0, 0, 0)
        age_width = 40
        self.cell(age_width, 10, age, 0, 0, 'L')  # No new line

        # Add some space between Age and Date
        self.set_x(60)  # Adjust X position to avoid overlap

        # Date label
        self.set_font("helvetica", "B", 10)
        self.set_text_color(*self.primary_color)
        date_label = "Date:"
        date_label_width = self.get_string_width(date_label) + 5
        self.cell(date_label_width, 10, date_label, 0, 0, 'L')

        # Date value
        self.set_font("helvetica", "", 10)
        self.set_text_color(0, 0, 0)
        self.cell(40, 10, date, 0, 1, 'L')  # End line

        # Patient info line
        self.line(10, 65, self.w - 10, 65)
        self.ln(5)

        # Patient Details section - separated into two columns
        self.set_y(70)  # Adjusted from original 60
        self.set_font("helvetica", "B", 10)
        self.set_text_color(*self.primary_color)

        # Left column - abbreviations
        left_col_width = 35  # Reduced width for left column
        self.set_x(10)
        self.cell(left_col_width, 10, "C/C", 0, 1, 'L')
        self.set_x(10)
        self.ln(10)
        self.set_x(10)
        self.cell(left_col_width, 10, "D/E", 0, 1, 'L')
        self.set_x(10)
        self.cell(left_col_width, 10, "BP=", 0, 1, 'L')

        # Vertical divider between columns - adjusted position
        self.set_draw_color(*self.primary_color)
        self.line(45, 70, 45, 160)  # Adjusted position and height

        # Main content area - Right column 
        # Patient Details using multi-cells for longer text
        patient_fields = [
            ('Chief Complaints:', 'chief_complaints'),
            ('Aggravating factor:', 'aggravating_factor'),
            ('Present Illness:', 'present_illness'),
            ('Family History:', 'family_history'),
            ('Surgical History:', 'surgical_history'),
            ('Examination:', 'examination'),
            ('Clinical Impression:', 'clinical_impression')
        ]

        self.set_y(70)  # Start right at 70 instead of 60
        self.set_x(50)  # Move content start to the right of the vertical line
        self.set_font("helvetica", "", 10)
        self.set_text_color(0, 0, 0)

        y_position = self.get_y()
        for label, field in patient_fields:
            self.set_font("helvetica", "B", 10)
            self.set_y(y_position)
            self.set_x(50)  # Adjusted from 75
            self.set_text_color(*self.secondary_color)
            self.cell(40, 8, label, 0, 0)
            self.set_font("helvetica", "", 10)
            self.set_text_color(0, 0, 0)
            self.set_x(90)  # Adjusted from 115
            self.multi_cell(100, 8, str(self.patient_data.get(field, '')))  # Increased width from 80 to 100
            y_position += 15

        # Advice (Medications Table)
        self.ln(5)
        self.set_font("helvetica", "B", 14)
        self.set_text_color(*self.primary_color)
        self.cell(0, 10, "Advice", 0, 1)

        # Prepare table data
        table_data = [
            ["S.No.", "Medicine Name", "Dosage", "Details"]
        ]
        for i, med in enumerate(self.advice_data):
            table_data.append([
                str(i + 1),
                med.get('name', ''),
                str(med.get('dosage', '')),
                med.get('details', '')
            ])

        self.create_table(table_data, align_data='C', align_header='C', cell_width='even')

        if output_path:
            return self.output(output_path)
        else:
            return bytes(self.output(dest='S'))


class PreviousPatientReport(PatientReport):
    
    def header(self):
        # Override the default header method to use our custom previous reports header
        # self.ln(10)
        margin = 10
        # Set green background for header
        self.set_fill_color(*self.primary_color)
        self.rect(0, 0, self.w, 40, 'F')
        
        # Add white text
        self.set_y(15)
        self.set_font("helvetica", "B", 18)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, "Previous Consultations", 0, 1, 'C')
        
        # Logo with white background
        if self.logo_data:
            self.set_fill_color(255, 255, 255)
            self.rect(margin, margin, 35, 35, 'F')
            self.image(self.logo_data, margin+2.5, margin+2.5, 30)

    

    def footer(self):
        # Override the default footer method to use our custom previous reports footer
        self.set_fill_color(*self.light_grey)
        self.rect(0, self.h - 15, self.w, 15, 'F')
        
        self.set_y(self.h - 12)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(0,0,0)
        self.cell(0, 10, "Page " + str(self.page_no()), 0, 0, "C")
        # self.ln(30)

    def generate_report(self):
        """Generate previous reports PDF and return as bytes"""
        self.add_page()
        
        start_y = self.get_y() + 30
        self.set_y(start_y)
        
        self.set_fill_color(*self.light_accent)
        self.rect(10, start_y, self.w - 20, 10, 'F')

        # Patient info header
        self.set_font("helvetica", "B", 10)
        self.set_text_color(*self.primary_color)
        self.cell(80, 10, "Patient Name:", 0, 0, 'L')
        self.cell(60, 10, "UHID:", 0, 0, 'L')
        self.cell(40, 10, "Age/Sex:", 0, 1, 'L')

        # Info line
        self.set_draw_color(*self.primary_color)
        self.line(10, start_y + 10, self.w - 10, start_y + 10)

        # Fill in patient details
        self.set_y(start_y + 15)
        self.set_font("helvetica", "", 10)
        self.set_text_color(0, 0, 0)
        self.cell(80, 10, self.patient_data.get('name', ''), 0, 0, 'L')
        self.cell(60, 10, self.patient_data.get('uhid', ''), 0, 0, 'L')
        self.cell(40, 10, str(self.patient_data.get('age', '') + '/' + self.patient_data.get('sex', '')), 0, 1, 'L')

        self.ln(10)

        # Previous Consultations - formatted as blocks
        self.set_font("helvetica", "B", 14)
        self.set_text_color(*self.primary_color)
        self.cell(0, 10, "Previous Consultations", 0, 1)

        self.set_font("helvetica", "", 10)
        self.set_text_color(0, 0, 0)

        for report in self.previous_reports:
            # Check for page break
            if self.get_y() + 30 > self.h - self.b_margin:
                self.add_page()
                self.set_y(50)

            date_hospital = f"{report.get('date', '')} - {report.get('hospital', '')}"
            consultation = report.get('consultation', '')

            # Calculate rectangle height more accurately
            available_width = self.w - 30  # Width of the rectangle minus some padding
            line_height = 8  # Height of each line
            
            # Function to calculate lines needed for text
            def calculate_text_height(text, width):
                if not text:
                    return 0
                    
                # Split text into paragraphs
                paragraphs = text.split('\n')
                total_lines = 0
                
                for paragraph in paragraphs:
                    # Skip empty paragraphs
                    if not paragraph.strip():
                        total_lines += 1
                        continue
                        
                    # Calculate how many lines this paragraph will take
                    text_width = self.get_string_width(paragraph)
                    # More accurate calculation - use ceiling division
                    lines_needed = max(1, (text_width / width) if text_width <= width else (text_width / width))
                    # Round up only if there's a partial line
                    total_lines += math.ceil(lines_needed)
                    
                return total_lines * line_height
            
            # Calculate the total height needed
            text_height = calculate_text_height(consultation, available_width)

    # Add header height (for date/hospital) + padding - reduce values
            rect_height = 10 + text_height + 5

            # Ensure minimum rectangle height - reduce for small content
            min_height = 20 if text_height < 10 else 30
            rect_height = max(rect_height, min_height)
            
            current_y = self.get_y()
            
            # Draw rounded rectangle
            self.set_fill_color(*self.light_accent)
            self.rounded_rect(10, current_y, self.w - 20, rect_height, 5, 'F')

            # Date and hospital on one line
            self.set_font("helvetica", "B", 12)
            self.set_text_color(*self.secondary_color)
            self.cell(0, 10, date_hospital, 0, 1, 'L')

            # Consultation description below
            self.set_font("helvetica", "", 10)
            self.set_text_color(0, 0, 0)
            self.multi_cell(available_width, line_height, consultation, 0, 'L')

            # Position for next item - calculate properly
            self.set_y(current_y + rect_height + 5)

        return bytes(self.output(dest='S'))

    def rounded_rect(self, x, y, w, h, r, style=None):
        """Draw a rectangle with rounded corners.
        
        Args:
            x, y: top-left corner coordinates
            w, h: width and height
            r: radius of the rounded corners
            style: 'F' for filled, 'S' for stroke (outline), 'DF' or 'FD' for both
        """
        # Ensure radius doesn't exceed dimensions
        r = min(r, min(w, h) / 2)
        
        # Start at top-right corner after the rounded part
        hp = self.h  # Page height
        k = self.k   # Scale factor
        
        # Move to position just after the top-left rounded corner
        self._out(f'{(x+r)*k:.2f} {(hp-y)*k:.2f} m')
        
        # Draw top border line (to top-right corner minus radius)
        self._out(f'{(x+w-r)*k:.2f} {(hp-y)*k:.2f} l')
        
        # Draw quarter circle for top-right rounded corner
        self._out(f'{(x+w-r)*k:.2f} {(hp-y)*k:.2f} {(x+w)*k:.2f} {(hp-y)*k:.2f} {(x+w)*k:.2f} {(hp-(y+r))*k:.2f} c')
        
        # Draw right border line (to bottom-right corner minus radius)
        self._out(f'{(x+w)*k:.2f} {(hp-(y+h-r))*k:.2f} l')
        
        # Draw quarter circle for bottom-right rounded corner
        self._out(f'{(x+w)*k:.2f} {(hp-(y+h-r))*k:.2f} {(x+w)*k:.2f} {(hp-(y+h))*k:.2f} {(x+w-r)*k:.2f} {(hp-(y+h))*k:.2f} c')
        
        # Draw bottom border line (to bottom-left corner minus radius)
        self._out(f'{(x+r)*k:.2f} {(hp-(y+h))*k:.2f} l')
        
        # Draw quarter circle for bottom-left rounded corner
        self._out(f'{(x+r)*k:.2f} {(hp-(y+h))*k:.2f} {x*k:.2f} {(hp-(y+h))*k:.2f} {x*k:.2f} {(hp-(y+h-r))*k:.2f} c')
        
        # Draw left border line (to top-left corner minus radius)
        self._out(f'{x*k:.2f} {(hp-(y+r))*k:.2f} l')
        
        # Draw quarter circle for top-left rounded corner
        self._out(f'{x*k:.2f} {(hp-(y+r))*k:.2f} {x*k:.2f} {(hp-y)*k:.2f} {(x+r)*k:.2f} {(hp-y)*k:.2f} c')
        
        # Close path and apply style
        if style == 'F':
            self._out('f')  # Fill
        elif style == 'S':
            self._out('S')  # Stroke
        else:  # 'FD' or 'DF'
            self._out('B')  # Both fill and stroke

# Function to generate report from JSON data
def generate_main_report_from_json(json_data):
    report = MainPatientReport(json_data)
    return report.generate_main_report()

def generate_previous_reports_from_json(json_data):
    # Create a completely separate instance for previous reports
    report = PreviousPatientReport(json_data)
    return report.generate_report()


@app.post("/generate_main_report")
async def generate_main_report_route(request: Request):
    try:
        json_data = await request.json()
        if not json_data:
            raise HTTPException(status_code=400, detail="No JSON data provided")

        main_report_bytes = generate_main_report_from_json(json_data)

        return Response(content=main_report_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=main_report.pdf"})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/generate_previous_reports")
async def generate_previous_reports_route(request: Request):
    try:
        json_data = await request.json()
        if not json_data:
            raise HTTPException(status_code=400, detail="No JSON data provided")

        previous_reports_bytes = generate_previous_reports_from_json(json_data)

        return Response(content=previous_reports_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=previous_reports.pdf"})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/")
async def read_root():
    return FileResponse("index.html")

@app.head("/generate_report")  
async def generate_report_head(request: Request):
    """Handles HEAD requests for the /generate_report endpoint."""
    return Response(status_code=200)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)