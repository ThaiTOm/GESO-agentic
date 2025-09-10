from dotenv import load_dotenv
load_dotenv()

from graph.main_graph import build_graph

app = build_graph()