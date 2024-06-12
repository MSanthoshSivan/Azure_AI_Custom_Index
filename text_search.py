import io
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.search.documents.models import VectorizedQuery
from azure.search.documents import SearchClient, SearchIndexingBufferedSender 
from azure.search.documents.indexes import SearchIndexClient
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

import pandas as pd


import sys
from io import BytesIO
import json
import os
# from IPython.display import Image
from PIL import Image
import csv
import datetime
from dotenv import load_dotenv

load_dotenv()

# Variables not used here do not need to be updated in your .env file
endpoint = os.environ["AZURE_SEARCH_SERVICE_ENDPOINT"]
credential = AzureKeyCredential(os.environ["AZURE_SEARCH_ADMIN_KEY"]) if len(os.environ["AZURE_SEARCH_ADMIN_KEY"]) > 0 else DefaultAzureCredential()
index_name = os.environ["AZURE_SEARCH_INDEX"]
blob_connection_string = os.environ["BLOB_CONNECTION_STRING"]
blob_container_name = os.environ["BLOB_CONTAINER_NAME"]
azure_openai_key = os.environ["AZURE_OPENAI_API_KEY"]
azure_openai_endpoint = os.environ["AZURE_OPENAI_API_ENDPOINT"]
azure_openai_embedding_deployment = os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME"]

def now():
    return datetime.datetime.now()

def get_text_embeddings(input_text : str):
    import os
    from openai import AzureOpenAI

    client = AzureOpenAI(
    api_key = azure_openai_key,  
    api_version = "2024-02-15-preview",
    azure_endpoint =azure_openai_endpoint
    )

    response = client.embeddings.create(
        input = input_text,
        model= azure_openai_embedding_deployment
    )

    return response.data[0].embedding

## Generate image embeddings and create a list of documents
descriptions = []
print(f"Reading the CSV file & Create Embeddings... {now()}")

try:
    # connection_string = os.environ["blob_connection_string"]
    # container_name = os.environ["blob_container_name"]
    blob_name = os.environ["BLOB_FILE_NAME"]
    blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
    blob_client = blob_service_client.get_blob_client(blob_container_name, blob_name)
    stream = blob_client.download_blob().readall()
    data = pd.read_csv(io.BytesIO(stream),skiprows=0)

    # print(data)
    # with open("../ESA FAQs QnA.csv", "r", encoding="utf-8") as file:
    #     next(file)
    # reader =  csv.reader(data, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

    i=0
    for index, row in data.iterrows():
        Query = row['Query']            
        Answer = row['Answer']
        if (index < 2):
            print(Query)
            print(Answer)
        descriptions.append({
            "id":str(index),
            "Query": Query,
            "Answer": Answer,
            "query_vector": get_text_embeddings(Query),
            "answer_vector": get_text_embeddings(Answer)
        })
        # i=i+1
        print (index, end=" ", flush=True)
        # Trobleshotting whether the index is creating or not
        # if (index>2):
        #     break

        
        # print(f"\nUploaded {len(descriptions)} documents in total {now()}")
except Exception as ex:
    print('Exception:')
    print(ex)
    
    
print(f"\nwriting to json file....{now()}")
with open("text.json", "w") as file:
    json.dump(descriptions, file)
print("Reading from Json file and storing in the array")
# Upload some documents to the index  
with open('./text.json', 'r') as file:
    descriptions = json.load(file) 

print(f"Uploading to Azure Search {now()}")
## Upload the image embeddings to AI Search
search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)
results = search_client.upload_documents(descriptions)
# Create a search client
search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)

# Get the document count
document_count = search_client.get_document_count()

# Print the document count
print(f"Upload completed with {document_count} documents Indexed...")
print(f"Upload completed {now()}")

# for result in results:
#     print(f'Indexed {result.key} with status code {result.status_code}')
  
# Use SearchIndexingBufferedSender to upload the documents in batches optimized for indexing  
"""with SearchIndexingBufferedSender(  
    endpoint=endpoint,  
    index_name=index_name,  
    credential=credential,  
) as batch_client:  
    # Add upload actions for all documents  
    batch_client.upload_documents(documents=documents)  
print(f"Uploaded {len(documents)} documents in total") """