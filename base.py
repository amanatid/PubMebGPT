"""Read Pubmed Papers."""
from typing import List, Optional

from llama_index.readers.base import BaseReader
from llama_index.readers.schema.base import Document


class PubmedReader_mod(BaseReader):
    """Pubmed Reader.

    Gets a search query, return a list of Documents of the top corresponding scientific papers on Pubmed.
    """

    def load_data_bioc(
        self,
        search_query: str,
        max_results: Optional[int] = 50,
    ) -> List[Document]:
        """Search for a topic on Pubmed, fetch the text of the most relevant full-length papers.
        Uses the BoiC API, which has been down a lot.

        Args:
            search_query (str): A topic to search for (e.g. "Alzheimers").
            max_results (Optional[int]): Maximum number of papers to fetch.

        Returns:
            List[Document]: A list of Document objects.
        """
        from datetime import datetime
        import xml.etree.ElementTree as xml

        import requests

        pubmed_search = []
        parameters = {"tool": "tool", "email": "email", "db": "pmc"}
        parameters["term"] = search_query
        parameters["retmax"] = max_results
        resp = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params=parameters,
        )
        root = xml.fromstring(resp.content)

        for elem in root.iter():
            if elem.tag == "Id":
                _id = elem.text
                try:
                    resp = requests.get(
                        f"https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/PMC{_id}/ascii"
                    )
                    info = resp.json()
                    title = "Pubmed Paper"
                    try:
                        title = [
                            p["text"]
                            for p in info["documents"][0]["passages"]
                            if p["infons"]["section_type"] == "TITLE"
                        ][0]
                    except KeyError:
                        pass
                    pubmed_search.append(
                        {
                            "title": title,
                            "url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{_id}/",
                            "date": info["date"],
                            "documents": info["documents"],
                        }
                    )
                except Exception:
                    print(f"Unable to parse PMC{_id} or it does not exist")
                    pass

        # Then get documents from Pubmed text, which includes abstracts
        pubmed_documents = []
        for paper in pubmed_search:
            for d in paper["documents"]:
                text = "\n".join([p["text"] for p in d["passages"]])
                pubmed_documents.append(
                    Document(
                        text,
                        extra_info={
                            "Title of this paper": paper["title"],
                            "URL": paper["url"],
                            "Date published": datetime.strptime(
                                paper["date"], "%Y%m%d"
                            ).strftime("%m/%d/%Y"),
                        },
                    )
                )

        return pubmed_documents

    def load_data(
        self,
        search_query: str,
        max_results: Optional[int] = 10,
        search_criterion : Optional[int] = 0
    ) -> List[Document]:
        """Search for a topic on Pubmed, fetch the text of the most relevant full-length papers.
        Args:
            search_query (str): A topic to search for (e.g. "Alzheimers").
            max_results (Optional[int]): Maximum number of papers to fetch.
        Returns:
            List[Document]: A list of Document objects.
        """
        import time
        import xml.etree.ElementTree as xml

        import requests

        if search_criterion == 0:
            sort_criterion ='relevance'

        if search_criterion == 1:
            sort_criterion = 'pub_date'

        if search_criterion == 2:
            sort_criterion = 'Journal'

        pubmed_search = []
        parameters = {"tool": "tool", "email": "email", "db": "pmc"}
        parameters["term"] = search_query
        parameters["retmax"] = max_results
        parameters["sort"] = sort_criterion

        # relevance:“Best Match”,  pub_date: descending sort by publication date,
        # Author – ascending sort by first author JournalName – ascending sort by journal name
        # https: // www.ncbi.nlm.nih.gov / books / NBK25499 /
        #print(parameters)

        resp = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params=parameters,
        )

        root = xml.fromstring(resp.content)

        for elem in root.iter():

            if elem.tag == "Id":
                _id = elem.text
                url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?id={_id}&db=pmc"
               # print(url)
                try:
                    resp = requests.get(url)
                    info = xml.fromstring(resp.content)

                    raw_text = ""
                    title = ""
                    journal = ""
                    for element in info.iter():
                        if element.tag == "article-title":
                            title = element.text
                        elif element.tag == "journal-title":
                            journal = element.text

                        if element.text:
                            raw_text += element.text.strip() + " "
                    #print(f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{_id}/")
                    pubmed_search.append(
                        {
                            "title": title,
                            "journal": journal,
                            "url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{_id}/",
                            "text": raw_text,
                        }
                    )
                    time.sleep(1)  # API rate limits
                except Exception as e:
                    print(f"Unable to parse PMC{_id} or it does not exist:", e)
                    pass

        # Then get documents from Pubmed text, which includes abstracts
        pubmed_documents = []
        for paper in pubmed_search:
            pubmed_documents.append(
                Document(
                    paper["text"],
                    extra_info={
                        "Title of this paper": paper["title"],
                        "Journal it was published in:": paper["journal"],
                        "URL": paper["url"],
                    },
                )
            )

        return pubmed_documents