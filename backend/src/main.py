import uvicorn
from fastapi import FastAPI, Response
import requests
import json
import base64
from markupsafe import Markup
import xml.etree.ElementTree as ET

from utils.xml_validator import content_validation, schema_validation, _create_temporary_file
from schemas import ResponseXmlSign, ResponseXmlSend, ResponseXmlCdr

# Lycet
TOKEN_LYCET= '123456'
BASE_PATH_LYCET='http://localhost:8001/api/v1/'

# Qpse
USER_QPSE = 'A10LKSRT'
PASS_QPSE = 'JLZFVTSP'
BASE_PATH_QPSE = 'https://demo-cpe.qpse.pe/'

ERROR_MESSAGES = {
    'request':'Error de comunicacion con microservici',
    'json_decode': 'No se pudo decodificar la respuesta recibida',
    'response_code': 'Microservicio retorno mensaje de error:'
}

app = FastAPI()

@app.get("/")
async def root():
    return {'message': 'Hello World'}

@app.post("/api/v1/invoice/xml")
async def create_invoice(data: dict):
    # send data to lycet api
    json_data = json.dumps(data)
    file_name = ('%s-%s-%s-%s')%(data['company']['ruc'],data['tipoDoc'],data['serie'],data['correlativo'])
    doc_type = data['tipoDoc']
    res = await send_json_and_receive_xml(json_data, doc_type)
    if res.get('error'):
        return Response(content=json.dumps(res), media_type='application/json')
    xml = res.get('xml')
    # -- Validate XML --
    xml_validate = _validate_xml(xml, file_name, doc_type)
    if xml_validate.get('error'):
        return Response(content=json.dumps(xml_validate), media_type='application/json')
    # -- End Validate XML --
    
    xml = _clean_xml(xml)

    base64_encoded = base64.b64encode(xml)
    base64_str = base64_encoded.decode('utf-8')

    # send xml to qpse api and get signed xml
    signed_xml = await send_xml_and_receive_signed_xml(base64_str, file_name)
    if signed_xml.get('error'):
        return Response(content=json.dumps(signed_xml), media_type='application/json')
    r_signed_xml = ResponseXmlSign(**signed_xml)
    if r_signed_xml.estado == 200:
        r_send_xml = await send_signed_xml_and_receive_cdr(r_signed_xml.xml, file_name)
        if r_send_xml.get('error'):
            return Response(content=json.dumps(r_send_xml), media_type='application/json')
        if r_send_xml.get('ticket'):
            r_send_xml['cdr'] = ''
        else:
            r_send_xml['ticket'] = ''
        r_send_xml = ResponseXmlSend(**r_send_xml)
    response = ResponseXmlCdr(xml_signed=r_signed_xml, cdr=r_send_xml)
    return response.model_dump()

@app.post('/api/v1/summary/xml')
async def create_summary(data: dict):
    json_data = json.dumps(data)
    file_name = ('%s')%(data['correlativo'])
    doc_type = 'summary'
    res = await send_json_and_receive_xml(json_data,doc_type)
    if res.get('error'):
        return Response(content=json.dumps(res), media_type='application/json')
    xml = res.get('xml')
    # -- Validate XML --
    xml_validate = _validate_xml(xml, file_name, doc_type)
    if xml_validate.get('error'):
        return Response(content=json.dumps(xml_validate), media_type='application/json')
    # -- End Validate XML --
    
    xml = _clean_xml(xml)

    base64_encoded = base64.b64encode(xml)
    base64_str = base64_encoded.decode('utf-8')

    # send xml to qpse api and get signed xml
    signed_xml = await send_xml_and_receive_signed_xml(base64_str, file_name)
    if signed_xml.get('error'):
        return Response(content=json.dumps(signed_xml), media_type='application/json')
    r_signed_xml = ResponseXmlSign(**signed_xml)
    if r_signed_xml.estado == 200:
        r_send_xml = await send_signed_xml_and_receive_cdr(r_signed_xml.xml, file_name)
        if r_send_xml.get('error'):
            return Response(content=json.dumps(r_send_xml), media_type='application/json')
        if r_send_xml.get('ticket'):
            r_send_xml['cdr'] = ''
        else:
            r_send_xml['ticket'] = ''
        r_send_xml = ResponseXmlSend(**r_send_xml)
    response = ResponseXmlCdr(xml_signed=r_signed_xml, cdr=r_send_xml)
    return response.model_dump()


def _validate_xml(xml, file_name, doc_type):
    """
    Validates the given XML against a schema and checks its content.

    Args:
        xml (str): The XML content to validate.
        file_name (str): The name of the XML file.
        doc_type (str): The type of document being validated.

    Returns:
        dict: A dictionary containing the validation result. If the XML is valid, the dictionary
            will have the key 'isValid' set to True and the key 'errors' set to an empty list.
            If the XML is invalid, the dictionary will have the key 'error' set to a string
            containing the validation errors.
    """
    # Validate schema
    if doc_type != 'summary':
        schema_errors = schema_validation(xml, doc_type)
        if schema_errors.get('isValid') == False:
            return {'error': '-'.join(schema_errors.get('errors')) }
    # Validate content
    content_errors = content_validation(xml, file_name, doc_type)
    if content_errors.get('isValid') == False:
        return {'error': '-'.join(content_errors.get('errors')) }
    return {'isValid': True, 'errors': []}

async def send_json_and_receive_xml(json_data, doc_type): # doc_type = '01','03','08','07' or 'summary'
    headers = {'Content-Type':'application/json', 'Accept':'application/xml'}
    url = ("%sinvoice/xml?token=%s")% (BASE_PATH_LYCET, TOKEN_LYCET)
    url.replace('invoice', 'summary') if doc_type == 'summary' else url
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.request('POST', url=url, headers=headers, data=json_data, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {'error':str(Markup("%s<br/>%s")%(ERROR_MESSAGES['request'], str(e)))}
    return {'xml': response.content.decode('utf-8')}

async def _get_qps_token():

    url = "%s/api/auth/cpe/token"% BASE_PATH_QPSE

    payload = json.dumps({
    "usuario": USER_QPSE,
    "contraseña": PASS_QPSE
    })
    headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json'
    }
    try:
        response = requests.request("POST", url, headers=headers, data=payload, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {'error':str(Markup("%s<br/>%s")%(ERROR_MESSAGES['request'], str(e)))}
    if response.status_code != 200:
        return {'error':str(Markup("%s<br/>%s")%(ERROR_MESSAGES['response_code'], response.text))}
    try:
        response_json = response.json()
    except ValueError as e:
        return {'error':str(Markup("%s<br/>%s")%(ERROR_MESSAGES['json_decode'], str(e)))}
    return response_json

async def send_xml_and_receive_signed_xml(xml, doc_name):

    # Get token
    token = await _get_qps_token()
    if token.get('error'):
        return token
    if token.get('token_acceso'):
        token = token.get('token_acceso')
    else: return {'error': 'No se pudo obtener el token de acceso'}


    url = "%sapi/cpe/generar"% BASE_PATH_QPSE
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer '+token
    }
    payload = json.dumps({
        "tipo_integracion": 0,
        "nombre_archivo": doc_name, # 10417844398-01-F001-17
        "contenido_archivo": xml
    })
    try:
        response = requests.request("POST", url, headers=headers, data=payload, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {'error':str(Markup("%s<br/>%s")%(ERROR_MESSAGES['request'], str(e)))}
    if response.status_code != 200:
        return {'error':str(Markup("%s<br/>%s")%(ERROR_MESSAGES['response_code'], response.text))}
    try:
        response_json = response.json()
    except ValueError as e:
        return {'error':str(Markup("%s<br/>%s")%(ERROR_MESSAGES['json_decode'], str(e)))}
    # response_json to dict
    if response_json['estado'] != 200:
        return {'error':str(Markup("%s<br/>%s")%(ERROR_MESSAGES['response_code'], response_json.get('mensaje').value))}
    return response_json

async def send_signed_xml_and_receive_cdr(signed_xml,doc_name):
    # Get token
    token = await _get_qps_token()
    if token.get('error'):
        return token
    if token.get('token_acceso'):
        token = token.get('token_acceso')
    else: return {'error': 'No se pudo obtener el token de acceso'}

    url = "%sapi/cpe/enviar"% BASE_PATH_QPSE
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer '+token
    }
    payload = json.dumps({
        'nombre_xml_firmado': doc_name,
        'contenido_xml_firmado': signed_xml
        })
    try:
        response = requests.request("POST", url, headers=headers, data=payload, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {'error':str(Markup("%s<br/>%s")%(ERROR_MESSAGES['request'], str(e)))}
    if response.status_code != 200:
        return {'error':str(Markup("%s<br/>%s")%(ERROR_MESSAGES['response_code'], response.text))}
    try:
        response_json = response.json()
    except ValueError as e:
        return {'error':str(Markup("%s<br/>%s")%(ERROR_MESSAGES['json_decode'], str(e)))}
    # response_json to dict
    if response_json['estado'] != 200:
        return {'error':str(Markup("%s<br/>%s")%(ERROR_MESSAGES['response_code'], response_json.get('mensaje').value))}
    return response_json

def _clean_xml(xml):
    """
    Cleans the given XML by removing the Signature element and modifying the XML declaration.

    Args:
        xml (str): The XML string to be cleaned.

    Returns:
        str: The cleaned XML string.
    """
    xml = xml.replace("<?xml version='1.0' encoding='utf-8'?>", "<?xml version='1.0' encoding='utf-8' standalone='no'?>")
    namespaces = {
        '': 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2',
        'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
        'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        'ds': 'http://www.w3.org/2000/09/xmldsig#',
        'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2'
    }
    ET.register_namespace('', 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2')
    ET.register_namespace('cac', 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2')
    ET.register_namespace('cbc', 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2')
    ET.register_namespace('ds', 'http://www.w3.org/2000/09/xmldsig#')
    ET.register_namespace('ext', 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2')

    root = ET.fromstring(xml)
    extensions = root.find('.//ext:ExtensionContent', namespaces=namespaces)
    # remove Signature
    if extensions is not None:
        extensions.clear()

    xml = ET.tostring(root, encoding='utf-8', method='xml', xml_declaration=True)
    return xml

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)