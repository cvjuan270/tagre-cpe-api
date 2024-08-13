import subprocess
import json, re, os, tempfile, base64
import xml.etree.ElementTree as ET
from markupsafe import Markup

saxon_jar = os.path.abspath('backend/saxon/saxon-he-12.4.jar')
XSL_PATHS  = {
    'xsl_file_01' : os.path.abspath('backend/resources/xsl-2.1/commons/xsl/ValidaExprRegFactura-2.0.1.xsl'),
    'xsl_file_03' : os.path.abspath('backend/resources/xsl-2.1/commons/xsl/ValidaExprRegBoleta-2.0.1.xsl'),
    'xsl_file_07' : os.path.abspath('backend/resources/xsl-2.1/commons/xsl/ValidaExprRegNC-2.0.1.xsl'),
    'xsl_file_08' : os.path.abspath('backend/resources/xsl-2.1/commons/xsl/ValidaExprRegND-2.0.1.xsl'),
    'xsl_file_summary': os.path.abspath('backend/resources/xsl-2.1/ValidaExprRegSummary-1.1.0.xsl'),
    'xml_error_catalog': os.path.abspath('backend/resources/xsl-2.1/commons/cpe/catalogo/CatalogoErrores.xml'),

}

XSD_PATHS = {
    'xsd_file_01': os.path.abspath('backend/resources/xsd-2.1/maindoc/UBL-Invoice-2.1.xsd'),
    'xsd_file_03': os.path.abspath('backend/resources/xsd-2.1/maindoc/UBL-Invoice-2.1.xsd'),
    'xsd_file_07': os.path.abspath('backend/resources/xsd-2.1/maindoc/UBL-CreditNote-2.1.xsd'),
    'xsd_file_08': os.path.abspath('backend/resources/xsd-2.1/maindoc/UBL-DebitNote-2.1.xsd')
}

def _create_temporary_file(xml):
    # save xml temporal file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as temp:
        temp.write(xml.encode('utf-8'))
        xml_file = temp.name
    return xml_file
    
def content_validation(xml, file_name, doc_type):
    try:
        xml_file = _create_temporary_file(xml)
        command = f"java -jar {saxon_jar} -s:{xml_file} -xsl:{XSL_PATHS['xsl_file_%s'%doc_type]} nombreArchivoEnviado={file_name+'.xml'}"

        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output, _ = process.communicate()
        return_var = process.returncode

    except Exception as e:
        return {
            'isValid': False,
            'errors':['Error al ejecutar comado, Detalles: %s'%str(e)],
        }
    
    try:
        result = {
            'isValid': return_var == 0,
            'errors': []
        }
        pattern = r"errorCode (\d+)"
        output_lines = output.decode('utf-8').split('\n')
        for line in output_lines:
            match = re.search(pattern, line)
            if match:
                error_code = match.group(1)
                result['errors'].append(str(Markup('%s<br/>%s'%(match.string, get_error_message(error_code)))))

        return result
    except Exception as e:
        return {
            'isValid': False,
            'errors': ['Error al procesar salida, Detalles: %s'%str(e)]
        }


def schema_validation(xml, doc_type):
    try:
        xml_file = _create_temporary_file(xml)
        command = f"xmllint --schema {XSD_PATHS['xsd_file_%s'%doc_type]}  {xml_file} --noout 2>&1"
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output, _ = process.communicate()
        return_var = process.returncode
    except Exception as e:
        return {
            'isValid': False,
            'errors':['Error al ejecutar comado, Detalles: %s'%str(e)],
        }
    try:
        result = {
            'isValid': return_var == 0,
            'errors': []
        }
        for line in output.decode('utf-8').split('\n'):
            result['errors'].append(str(Markup(line+'<br/>')))
    except Exception as e:
        return {
            'isValid': False,
            'errors': ['Error al procesar salida, Detalles: %s'%str(e)]
        }

    return result

def get_error_message(error_code):
    tree = ET.parse(XSL_PATHS['xml_error_catalog'])
    root = tree.getroot()
    error = root.find(f"./error[@numero='{error_code}']")
    if error is not None:
        return error.text
    else:
        return None