import PyPDF2
import sys

def extract_text_from_pdf(pdf_path):
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text += page.extract_text() + "\n\n"
            return text
    except Exception as e:
        return f"Error extracting text: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_pdf.py <pdf_filename> [output_filename]")
        sys.exit(1)
        
    pdf_path = sys.argv[1]
    extracted_text = extract_text_from_pdf(pdf_path)
    
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        output_file = "pdf_content.txt"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(extracted_text)
        print(f"Text successfully extracted to {output_file}")
    except Exception as e:
        print(f"Error writing to file: {str(e)}") 