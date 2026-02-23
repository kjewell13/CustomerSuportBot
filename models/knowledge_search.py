from dataclasses import dataclass
import os, re
from typing import List, Dict, Any, Tuple

# regex pattern matching to find heading (# .....) or sub heading (## .....)
# capture just heading text -- # heading 1 -> heading 1
heading = re.compile(r"^#\s+(.*)\s*$", flags = re.IGNORECASE)
sub_heading = re.compile(r"^##\s+(.*)\s*$", flags = re.IGNORECASE)

@dataclass
class Chunk:
    filename: str
    title: str      # main heading
    section: str    # sub heading
    content: str

# default is knowledge for testing purposes, replace with wherever your company/product information files are

#returns List in form of (filename, content)
def read_files(folder: str = "knowledge") -> List[Tuple[str, str]]:
    files = []
    for file in os.listdir(folder):
        if(file.lower().endswith(".md")):
            path = os.path.join(folder, file)
            with open(path, "r", encoding = "utf-8") as f:
                files.append((file, f.read()))
    return files


def chunk_file(filename: str, content: str) -> List[Chunk]:
    lines = content.splitlines()

    # setting defualt title to filename if # main heading does not exist
    title = os.path.splitext(filename)[0]
    section: str | None = None
    # temporary buffer to handle content of each section
    buffer: list[str] = []
    

    chunks: list[Chunk] = []

    for line in lines:
        line = line.strip()

        # find title first, if not found resort to default of filename
        title_match = heading.match(line)
        if title_match:
            title = title_match.group(1).strip() # group(1) gives us only the captured part (no #)
            continue
        
        # matching sub_heading/section
        section_match = sub_heading.match(line)
        if section_match:
            section_content = "\n".join(buffer).strip()

            if section and section_content:
                chunks.append(Chunk(filename=filename, title=title, section=section, content=section_content))
                
                # reset buffer
            buffer = []
            section = section_match.group(1).strip()
            continue

        # regular line (non-header)
        buffer.append(line)

    # close final section -- no header after it
    final_content = "\n".join(buffer).strip()
    if section and final_content:
        chunks.append(Chunk(filename=filename, title=title, section=section, content=final_content))


    return chunks

# create list ofnormalized user query -- words >= 3 chars, no punctuation, lowercase
def tokenize(query: str) -> List[str]:
    return [w.lower() for w in re.findall(r"[a-zA-Z0-9]+", query) if len(w) >= 3]


# simple scoring based on keyword similarity -- should replace with cosine similarity and vector embeddings
def score_query(split_query: List[str], chunk: Chunk) -> int:
    text = (chunk.section+ "\n" + chunk.content).lower()
    score = 0
    for word in split_query:
        score += text.count(word)
    return score

def knowledge_search(query: str, top_k: int = 3, folder: str= "knowledge") -> Dict[str, Any]:
    files = read_files(folder)

    chunks: List[Chunk] = []

    for filename, content in files:
        chunks.extend(chunk_file(filename, content))

    terms = tokenize(query)

    scores: List[Tuple[int, Chunk]] = []
    for chunk in chunks:
        s = score_query(terms, chunk)
        if s > 0:
            scores.append((s, chunk))

    # in descending order
    scores.sort(key = lambda x: x[0], reverse = True)

    top_matches = []
    for score, chunk in scores[:top_k]:
        top_matches.append(chunk)

    

    final_matches = []
    for chunk in top_matches:
        content = chunk.content.strip()
        # to normalize larger repsponses
        if len(content) > 700:
            content = content[:700].rstrip() + "..."
        final_matches.append({"source" : chunk.filename, "title" : chunk.title, "section" : chunk.section, "content" : content})


    return {"query": query, "top_k" : top_k, "matches": final_matches}




        

