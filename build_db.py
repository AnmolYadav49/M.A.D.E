from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

# 1. Initialize the free local embedding model
print("Downloading embedding model (this takes a moment the first time)...")
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# 2. Create sample enterprise documentation
docs = [
    Document(page_content="Pandas Data Cleaning: To load a CSV, use pd.read_csv('file.csv'). To remove missing values across the entire dataframe, use df.dropna(inplace=True)."),
    Document(page_content="Scikit-Learn Model Training: To train a basic classifier, use from sklearn.ensemble import RandomForestClassifier. Initialize with clf = RandomForestClassifier(n_estimators=100) and fit using clf.fit(X_train, y_train)."),
    Document(page_content="Pandas Aggregation: To group data by a specific category and find the average, use df.groupby('category_column').mean().")
]

# 3. Build and save the FAISS index
print("Building FAISS Vector Database...")
vector_db = FAISS.from_documents(docs, embeddings)
vector_db.save_local("faiss_index")

print("Success! Vector DB saved to the 'faiss_index' directory.")