import json
import os
import time
from pathlib import Path #esto es para manejar rutas de archivos de manera más fácil

from dotenv import load_dotenv #esto es para cargar variables de entorno desde un archivo .env
from openai import OpenAI #esto es para usar el modelo de lenguaje de OpenAI
from jsonschema import validate #esto es para validar que la respuesta del modelo de lenguaje cumple con un esquema JSON específico     


PROMPTS_FILES = [Path("prompts/main_prompt.md"), Path("prompts/main_prompt.txt")]  #esto es para definir la ruta del directorio donde se guardan los prompts

def load_prompts():
    for prompt_file in PROMPTS_FILES:
        if prompt_file.exists():
            with open(prompt_file, "r") as f: #esto es para abrir el archivo de prompts y leer su contenido
                return f.read() #esto es para devolver el contenido del archivo de prompts como una cadena de texto
    raise FileNotFoundError("No prompt file found in the expected locations.")

def run_query(query):
    load_dotenv() #esto es para cargar las variables de entorno desde el archivo .env
    client = OpenAI() #esto es para crear una instancia del cliente de OpenAI
    prompts = load_prompts() #esto es para cargar los prompts desde el archivo de prompts
    prompt = prompts.replace("{{QUESTION}}", query) #esto es para reemplazar la parte "{query}" en los prompts con la consulta real del usuario
    response = client.chat.completions.create( #esto es para crear una respuesta del modelo de lenguaje usando el cliente de OpenAI
        model="gpt-4-0613", #esto es para especificar el modelo de lenguaje que se va a usar
        messages=[{"role": "user", "content": prompt}], #esto es para enviar el prompt al modelo de lenguaje como un mensaje del usuario
        temperature=0.0003, #esto es para controlar la creatividad de la respuesta del modelo de lenguaje (valores más bajos hacen que la respuesta sea más predecible)
        max_tokens=1000, #esto es para limitar la cantidad de tokens en la respuesta del modelo de lenguaje
    )
    return response.choices[0].message.content.strip() #esto es para devolver el contenido de la respuesta del modelo de lenguaje como una cadena de texto sin espacios al principio o al final

if __name__ == "__main__":
    query = input("Soy un experto en teconlogia, ingresa tu pregunta: ") #esto es para pedir al usuario que ingrese su consulta
    response = run_query(query) #esto es para ejecutar la función run_query con la consulta del usuario y obtener la respuesta del modelo de lenguaje
    print("Response:") #esto es para imprimir un mensaje indicando que se va a mostrar la respuesta
    print(response) #esto es para imprimir la respuesta del modelo de lenguaje en la consola


