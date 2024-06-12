from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SimpleField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    SemanticSearch,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SearchIndex
)
from azure.core.exceptions import HttpResponseError

from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
import os
load_dotenv()

endpoint = os.environ["AZURE_SEARCH_SERVICE_ENDPOINT"]
credential = AzureKeyCredential(os.environ["AZURE_SEARCH_ADMIN_KEY"]) if len(os.environ["AZURE_SEARCH_ADMIN_KEY"]) > 0 else DefaultAzureCredential()
index_name = os.environ["AZURE_SEARCH_INDEX"]

azure_openai_key = os.environ["AZURE_OPENAI_API_KEY"]
azure_openai_endpoint = os.environ["AZURE_OPENAI_API_ENDPOINT"]
azure_openai_embedding_deployment = os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME"]

try:
    # Create a search index 
    index_client = SearchIndexClient(endpoint=endpoint, credential=credential) 
    fields = [  
        SimpleField(name="id", type=SearchFieldDataType.String, key=True), 
        # SearchField(name="Module", type=SearchFieldDataType.String, sortable=True, filterable=True, facetable=True),
        SearchField(name="Query", type=SearchFieldDataType.String, sortable=True, filterable=True, facetable=True),
        SearchField(name="Answer", type=SearchFieldDataType.String, searchable=True, sortable=False, filterable=True, facetable=True),
        SearchField(
            name="query_vector",  
            hidden=True,
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single), 
            searchable=True,
            vector_search_dimensions=1536,  
            vector_search_profile_name="myHnswProfile"
        ), 
        SearchField(
            name="answer_vector",  
            hidden=True,
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single), 
            searchable=True,
            vector_search_dimensions=1536,  
            vector_search_profile_name="myHnswProfile"
        ),  
    ]  
    
    # Configure the vector search configuration  
    vector_search = VectorSearch(  
        algorithms=[  
            HnswAlgorithmConfiguration(  
                name="myHnsw"
            )
        ],  
    profiles=[  
            VectorSearchProfile(  
                name="myHnswProfile",  
                algorithm_configuration_name="myHnsw",  
            )
        ],
        vectorizers=[
            {
            "name": "esa-custom-vectorizer",
            "kind": "azureOpenAI",
            "azureOpenAIParameters": {
                "resourceUri": azure_openai_endpoint,
                "deploymentId": azure_openai_embedding_deployment,
                "apiKey": azure_openai_key
            }
            }
        ]
    )

    # Configure the semantic search configuration
    semantic_config = SemanticConfiguration(
        name="esa-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="id"),
            keywords_fields=[SemanticField(field_name="Query")],
            content_fields=[SemanticField(field_name="Answer")]
        )
    )

    # Create the semantic settings with the configuration
    semantic_search = SemanticSearch(configurations=[semantic_config])
    
    # Create the search index with the vector search configuration  
    index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search, semantic_search=semantic_search) 

    #Checks if the index is already present if so, delete and create the index
    if index_client.get_index(index_name):
        index_client.delete_index(index_name)

    result = index_client.create_or_update_index(index)
    print(f"{result.name} created") 

except HttpResponseError as e:
    if e.status_code == 401:
        print("HTTP Error 401: Unauthorized. Please check your Azure credentials.")
    else:
        raise