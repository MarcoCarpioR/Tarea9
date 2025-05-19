import os
import re
import uuid
import tempfile
import xml.etree.ElementTree as ET
import pandas as pd
import PyPDF2
from bs4 import BeautifulSoup
from flask import Flask, request, render_template, send_file, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Crear carpeta temporal para almacenar archivos
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'xml_converter_uploads')
OUTPUT_FOLDER = os.path.join(tempfile.gettempdir(), 'xml_converter_outputs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER


def extraer_xml_de_pdf(pdf_ruta):
    try:
        with open(pdf_ruta, 'rb') as archivo:
            lector_pdf = PyPDF2.PdfReader(archivo)
            texto_completo = ""
            for pagina in lector_pdf.pages:
                texto_pagina = pagina.extract_text()
                if texto_pagina:
                    texto_completo += texto_pagina + " "

        # Limpiar la declaración XML incorrecta
        texto_limpio = re.sub(r'\$\s*=\s*\'\"(.*?)\"\'', r'="\1"', texto_completo)
        texto_limpio = re.sub(r'\$\s*=\s*\"\'(.*?)\'\"', r"='\1'", texto_limpio)
        texto_limpio = re.sub(r'file:\/\/.*$', '', texto_limpio, flags=re.MULTILINE)
        texto_limpio = texto_limpio.strip()

        if not texto_limpio:
            raise ValueError("No XML content found in PDF")

        # Extraer el contenido XML principal
        patron_xml = r'<\?xml version=(["\'])(.*?)\1 encoding=(["\'])(.*?)\3\?>\s*(.*)</\w+>'
        coincidencias = re.search(patron_xml, texto_limpio, re.DOTALL)

        if coincidencias:
            xml_contenido = f'<?xml version="{coincidencias.group(2)}" encoding="{coincidencias.group(4)}"?>{coincidencias.group(5)}'
        else:
            patron_simple = r'<(\w+).*?>([\s\S]*?)<\/\1>'
            coincidencias_simple = re.search(patron_simple, texto_limpio)
            if coincidencias_simple:
                xml_contenido = f'<?xml version="1.0" encoding="UTF-8"?>{texto_limpio}'
            else:
                raise ValueError("Could not extract valid XML content")

        return xml_contenido

    except Exception as e:
        print(f"Error al extraer XML del PDF: {str(e)}")
        return None


def xml_to_dataframe(xml_content):
    try:
        root = ET.fromstring(xml_content)
        data = []
        for element in root:  # Iterar sobre los hijos del elemento raíz
            row = {}
            for child in element:
                row[child.tag] = child.text
                if child.attrib:  # Si el hijo tiene atributos, agregarlos también
                    for attr_name, attr_value in child.attrib.items():
                        row[f'{child.tag}_{attr_name}'] = attr_value
            data.append(row)
        return pd.DataFrame(data)
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return pd.DataFrame()  # Return an empty DataFrame in case of error


def cargar_archivo(ruta):
    if not os.path.isfile(ruta):
        raise FileNotFoundError(f"Archivo no existe: {ruta}")

    extension = os.path.splitext(ruta)[1].lower()

    if extension == '.pdf':
        xml_contenido = extraer_xml_de_pdf(ruta)
        if xml_contenido is None:
            raise ValueError("No se pudo encontrar contenido XML válido en el archivo PDF")
        return xml_contenido
    else:
        with open(ruta, 'r', encoding='utf-8') as f:
            return f.read()


def validar_xml(xml):
    try:
        ET.fromstring(xml)
        return True, ""
    except ET.ParseError as e:
        return False, f"Error sintaxis XML: {e}"


def metodo_example(xml):
    xml_corr = xml.replace('&', '&amp;')
    root = ET.fromstring(xml_corr)  # Use ElementTree for parsing
    data = []
    for element in root.iter():
        if element.text and element.text.strip():
            data.append({'etiqueta': element.tag, 'texto': element.text.strip()})
    return pd.DataFrame(data)


def metodo_et(xml):
    root = ET.fromstring(xml)
    datos = {}
    for elem in root.iter():
        if elem.text and elem.text.strip():
            datos.setdefault(elem.tag, []).append(elem.text.strip())
    return datos


def metodo_minidom(xml):
    from xml.dom import minidom  # Import inside the function to avoid global dependency
    doc = minidom.parseString(xml)
    datos = {}
    for nodo in doc.getElementsByTagName('*'):
        if nodo.firstChild and nodo.firstChild.nodeValue.strip():
            datos.setdefault(nodo.tagName, []).append(nodo.firstChild.nodeValue.strip())
    return datos


def metodo_invalid1(xml):
    return xml.replace('&', '&amp;')


def metodo_invalid2(xml):
    sopa = BeautifulSoup(xml, 'lxml-xml')
    return sopa.prettify()


def exportar_csv(de, salida):
    if isinstance(de, dict):
        filas = [{'etiqueta': k, 'texto': t} for k, vs in de.items() for t in vs]
        df = pd.DataFrame(filas)
    else:
        df = de
    df.to_csv(salida, index=False)
    return salida


def exportar_json(de, salida):
    import json  # Import inside the function
    with open(salida, 'w', encoding='utf-8') as f:
        json.dump(de, f, ensure_ascii=False, indent=2)
    return salida


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo')
        return redirect(request.url)

    file = request.files['file']
    if file.filename == '':
        flash('No se seleccionó ningún archivo')
        return redirect(request.url)

    if file:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ['.xml', '.pdf']:
            flash('Solo se permiten archivos XML o PDF que contengan XML')
            return redirect(url_for('index'))

        filename = str(uuid.uuid4()) + '_' + file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            xml_content = cargar_archivo(filepath)
            valid, error_msg = validar_xml(xml_content)

            if not valid:
                flash(f"Error al validar XML: {error_msg}")
                os.remove(filepath)
                return redirect(url_for('index'))

            if ext == '.pdf':
                xml_filename = filename.replace('.pdf', '.xml')
                xml_filepath = os.path.join(app.config['UPLOAD_FOLDER'], xml_filename)
                with open(xml_filepath, 'w', encoding='utf-8') as f:
                    f.write(xml_content)
                os.remove(filepath)  # Eliminar el PDF original
                return redirect(url_for('process_file', filename=xml_filename))  # Redirect to processing

        except Exception as e:
            flash(f"Error al procesar el archivo: {str(e)}")
            if os.path.exists(filepath):
                os.remove(filepath)
            return redirect(url_for('index'))

        return redirect(url_for('process_file', filename=filename))


@app.route('/process/<filename>')
def process_file(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        flash('Archivo no encontrado')
        return redirect(url_for('index'))
    return render_template('process.html', filename=filename)


@app.route('/convert', methods=['POST'])
def convert():
    filename = request.form.get('filename')
    method = request.form.get('method')
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    nombre_archivo_original = filename.split('_', 1)[-1] if '_' in filename else filename
    base = os.path.splitext(nombre_archivo_original)[0]

    try:
        xml_content = cargar_archivo(filepath)

        if method == '1':  # Validar XML
            valid, error_msg = validar_xml(xml_content)
            if valid:
                flash('XML válido')
            else:
                flash(error_msg)
            return redirect(url_for('process_file', filename=filename))

        elif method == '2':  # Example -> CSV (using ElementTree)
            df = metodo_example(xml_content)
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{base}_example.csv")
            exportar_csv(df, output_path)
            return send_file(output_path, as_attachment=True, download_name=f"{base}_example.csv")

        elif method == '3':  # ElementTree -> Dict
            result = metodo_et(xml_content)
            return render_template('result.html', result=result, filename=filename, method="ElementTree")

        elif method == '4':  # MiniDOM -> Dict
            result = metodo_minidom(xml_content)
            return render_template('result.html', result=result, filename=filename, method="MiniDOM")

        elif method == '5':  # Invalid Method 1
            result = metodo_invalid1(xml_content)
            return render_template('text_result.html', result=result, filename=filename, method="Invalid Method 1")

        elif method == '6':  # Invalid Method 2
            result = metodo_invalid2(xml_content)
            return render_template('text_result.html', result=result, filename=filename, method="Invalid Method 2")

        elif method == '7':  # Export JSON (ET)
            result = metodo_et(xml_content)
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{base}.json")
            exportar_json(result, output_path)
            return send_file(output_path, as_attachment=True, download_name=f"{base}.json")

        elif method == '8':  # XML to DataFrame
            df = xml_to_dataframe(xml_content)
            if not df.empty:
                output_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{base}_data.csv")
                exportar_csv(df, output_path)
                return send_file(output_path, as_attachment=True, download_name=f"{base}_data.csv")
            else:
                flash('No se pudo convertir el XML a DataFrame.')
                return redirect(url_for('process_file', filename=filename))

        else:
            flash('Método no válido')
            return redirect(url_for('process_file', filename=filename))

    except Exception as e:
        flash(f"Error al procesar el archivo: {str(e)}")
        return redirect(url_for('process_file', filename=filename))


if __name__ == '__main__':
    app.run(debug=True)