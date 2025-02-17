from fpdf import FPDF, XPos, YPos
import textwrap
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse,Response
from fastapi.middleware.cors import CORSMiddleware
import base64
from fastapi.staticfiles import StaticFiles
from io import BytesIO 


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
        

    def create_table(self, table_data, title='', data_size=10, title_size=12, 
                     align_data='C', align_header='L', cell_width='even', 
                     x_start='x_default', emphasize_data=[], emphasize_style=None, 
                     emphasize_color=(0, 0, 0)):
        default_style = self.font_style
        if emphasize_style is None:
            emphasize_style = default_style

        # Get Width of Columns
        def get_col_widths():
            col_width = cell_width
            num_cols = len(table_data[0]) if table_data else 0
            if col_width == 'even':
                col_width = self.epw / num_cols - 1 if num_cols > 0 else 0
            elif col_width == 'uneven':
                col_widths = []
                for col in range(num_cols):
                    longest = 0
                    for row in range(len(table_data)):
                        cell_value = str(table_data[row][col])
                        value_length = self.get_string_width(cell_value)
                        if value_length > longest:
                            longest = value_length
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
            # need to zip so data is in correct format (first, second, third --> not first, first, first)
            data = [list(a) for a in zip(*data)]

        else:
            header = table_data[0]
            data = table_data[1:]

        line_height = self.font_size * 2.5

        col_width = get_col_widths()
        self.set_font(size=title_size)

        
        if x_start == 'C':
            table_width = 0
            if isinstance(col_width, list):
                for width in col_width:
                    table_width += width
            else: # need to multiply cell width by number of cells to get table width 
                table_width = col_width * len(table_data[0])
            # Get x start by subtracting table width from pdf width and divide by 2 (margins)
            margin_width = self.w - table_width
            # TODO: Check if table_width is larger than pdf width

            center_table = margin_width / 2 # only want width of left margin not both
            x_start = center_table
            self.set_x(x_start)
        elif isinstance(x_start, int):
            self.set_x(x_start)
        elif x_start == 'x_default':
            x_start = self.set_x(self.l_margin)


        # TABLE CREATION #

        # add title
        if title!= '':
            self.multi_cell(0, line_height, title, border=0, align='j', ln=3, max_line_height=self.font_size)
            self.ln(line_height) # move cursor back to the left margin

        self.set_font(size=data_size)
        # add header
        y1 = self.get_y()
        x_left = x_start if x_start != 'x_default' else self.l_margin
        if x_left is None:  # Handle None case
            x_left = self.l_margin if self.l_margin is not None else 10 # Provide a default value if l_margin is also None.
        x_right = self.epw + x_left if x_left is not None else self.epw + 10 # Use default value if x_left is None

        if isinstance(col_width, list):
            for i, datum in enumerate(header):
                self.multi_cell(col_width[i], line_height, datum, border=0, align=align_header, 
                                max_line_height=self.font_size, new_x=XPos.RIGHT, new_y=YPos.TOP) # Updated
        else:
            for datum in header:
                self.multi_cell(col_width, line_height, datum, border=0, align=align_header, 
                                max_line_height=self.font_size, new_x=XPos.RIGHT, new_y=YPos.TOP) # Updated
        self.ln(line_height)
        y2 = self.get_y()
        self.line(x_left, y1, x_right, y1)
        self.line(x_left, y2, x_right, y2)

        for row in data:
            x_left = x_start if x_start != 'x_default' else self.l_margin
            if x_left is None:
                x_left = self.l_margin if self.l_margin is not None else 10
            self.set_x(x_left)
            if isinstance(col_width, list):
                for i, datum in enumerate(row):
                    adjusted_col_width = col_width[i]
                    # ... (emphasize data handling - same as before)
                    self.multi_cell(adjusted_col_width, line_height, datum, border=0, align=align_data,
                                    max_line_height=self.font_size, new_x=XPos.RIGHT, new_y=YPos.TOP) # Updated
            else:
                for datum in row:
                    # ... (emphasize data handling - same as before)
                    self.multi_cell(col_width, line_height, datum, border=0, align=align_data,
                                    max_line_height=self.font_size, new_x=XPos.RIGHT, new_y=YPos.TOP) # Updated
            self.ln(line_height)
        y3 = self.get_y()
        self.line(x_left, y3, x_right, y3)

    def header(self):
        margin = 10
        available_width = self.w - 2 * margin
        logo_width = 30
        hospital_width = available_width * 0.5
        
        # Logo
        if self.logo_data:
            self.image(self.logo_data, margin, self.get_y(), 30)
        
        hos_width = logo_width + 10 * margin
        
        # Doctor Details
        self.set_y(10)
        self.set_font("times", "B", 9)
        self.cell(0, 5, self.doctor_data.get('name', ''), 0, 1, "C")
        self.set_font("times", "", 7)
        self.cell(0, 5, self.doctor_data.get('degree', ''), 0, 1, "C")
        self.cell(0, 5, self.doctor_data.get('speciality', ''), 0, 1, "C")
        self.cell(0, 5, f"Mobile: {self.doctor_data.get('mobile', '')}", 0, 1, "C")
        self.cell(0, 5, f"Email: {self.doctor_data.get('email', '')}", 0, 1, "C")
        self.cell(0, 5, f"PMC No. {self.doctor_data.get('pmc', '')}", 0, 1, "C")
        
        # Hospital Details
        self.set_y(10)
        self.set_x(hos_width)
        self.set_font("times", "B", 9)
        self.cell(hospital_width, 5, self.hospital_data.get('name', ''), 0, 1, "C")
        self.set_font("times", "", 7)
        self.set_x(hos_width)
        self.cell(hospital_width, 5, self.hospital_data.get('address', ''), 0, 1, "C")
        self.set_x(hos_width)
        self.cell(hospital_width, 5, f"Tel: {self.hospital_data.get('phone', '')}", 0, 1, "C")
        self.set_x(hos_width)
        self.cell(hospital_width, 5, f"Email: {self.hospital_data.get('email', '')}", 0, 1, "C")
        self.set_x(hos_width)
        self.cell(hospital_width, 5, f"Website: {self.hospital_data.get('website', '')}", 0, 1, "C")
        self.set_x(hos_width)
        self.cell(hospital_width, 5, f"Emergency: {self.hospital_data.get('emergency', '')}", 0, 1, "C")
        
        self.ln(5)
        self.line(10, self.get_y(), self.w - 10, self.get_y())
        self.ln(1)

    def footer(self):
        self.set_y(-30)
        self.line(10, self.get_y(), self.w - 10, self.get_y())
        
        footer_data = self.hospital_data.get('footer', {})
        
        self.set_font("times", "B", 10)
        self.cell(0, 5, footer_data.get('name', ''), 0, 1, "C")
        
        self.set_font("times", "", 10)
        self.cell(0, 5, footer_data.get('address', ''), 0, 1, "C")
        
        contact_line = f"E-mail: {footer_data.get('email', '')} | Tel: {footer_data.get('phone', '')}"
        self.cell(0, 5, contact_line, 0, 1, "C")
        
        self.set_font("times", "I", 8)
        self.cell(0, 10, "Page " + str(self.page_no()), 0, 0, "C")

    def generate_report(self, output_path=None):
        """Generate report and return PDF as bytes"""
        self.add_page()
        self.set_font("times", size=12)

        # Patient Details
        patient_fields = [
            ('Patient Name:', 'name'),
            ('UHID:', 'uhid'),
            ('Age/Sex:', 'age_sex'),
            ('Chief Complaints:', 'chief_complaints'),
            ('Aggravating factor:', 'aggravating_factor'),
            ('Present Illness:', 'present_illness'),
            ('Family History:', 'family_history'),
            ('Surgical History:', 'surgical_history'),
            ('Examination:', 'examination'),
            ('Clinical Impression:', 'clinical_impression')
        ]

        y_position = self.get_y()
        for label, field in patient_fields:
            self.set_font("times", "B", 12)
            self.set_y(y_position)
            self.cell(40, 10, label, 0, 0)
            self.set_font("times", "", 12)
            self.multi_cell(0, 10, str(self.patient_data.get(field, '')))
            y_position += 10

        # Advice (Medications Table)
        self.ln(5)
        self.set_font("times", "B", 12)
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

        # Previous Reports
        if self.previous_reports:
            self.add_page()
            self.set_font("times", "B", 12)
            self.cell(0, 10, "Previous Reports/Consultations", 0, 1)

            self.set_font("times", "", 10)
            for report in self.previous_reports:
                heading, content = report.split(":", 1) if ":" in report else ("Report", report)
                self.set_font("times", "B", 10)
                self.cell(0, 5, heading.strip() + ":", 0, 1)

                self.set_font("times", "", 10)
                wrapped_content = textwrap.wrap(content.strip(), 75)
                self.multi_cell(0, 5, "\n".join(wrapped_content), 0, 'L')
                self.ln(2)

        # Get PDF as bytes
        # pdf_bytes = self.output(dest='S')
        
        # Clean up temporary logo file if it exists
        
                
        if output_path:
            return self.output(output_path)
        else:
            return bytes(self.output(dest='S'))
        


# Function to generate report from JSON data
def generate_report_from_json(json_data, output_path=None):
    """
    Generate a PDF report from JSON data and return the PDF as bytes
    
    Args:
        json_data (dict or str): JSON data containing all report information
        
    Returns:
        bytes: PDF file as bytes
    """
    report = PatientReport(json_data)
    return report.generate_report(output_path)

@app.post("/generate_report")
async def generate_report_route(request: Request):
    try:
        json_data = await request.json()
        if not json_data:
            raise HTTPException(status_code=400, detail="No JSON data provided")

        report = PatientReport(json_data)

        # Use BytesIO to store PDF in memory
        pdf_buffer = BytesIO()
        report.generate_report(output_path=pdf_buffer)  # Save to buffer
        pdf_bytes = pdf_buffer.getvalue()  # Get PDF bytes from buffer

        # Return PDF directly using Response with correct content type
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=patient_report.pdf"})


    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
@app.get("/")
async def read_root():
    return FileResponse("index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True) 