# ielts_graph_builder.py

import random
from typing import List, Literal, Optional, Dict, Any, Union  # Ensure Union is imported for type hints
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

# Your custom LLM caller
from llm.llm_langchain import local_llm_service, gemini_llm_service

llm = gemini_llm_service


# --- Pydantic Models for Structured Output ---

class CueCard(BaseModel):
    topic: str = Field(description="The main topic for the candidate to talk about.")
    points: List[str] = Field(description="A list of 3-4 bullet points the candidate should cover in their talk.")


class IeltsFeedback(BaseModel):
    fluency_and_coherence: str = Field(
        description="Feedback on the user's ability to speak at length, connect ideas, and use cohesive devices.")
    lexical_resource: str = Field(
        description="Feedback on the user's range of vocabulary, use of idiomatic language, and paraphrasing skills.")
    grammatical_range_and_accuracy: str = Field(
        description="Feedback on the user's use of complex structures and grammatical accuracy.")
    overall_band_score: float = Field(
        description="An estimated overall band score for the speaking performance, e.g., 6.5, 7.0, 7.5.")
    final_summary: str = Field(description="A concluding summary with overall advice for improvement.")


# --- Graph State Definition ---

class IeltsState(TypedDict):
    user_response: str
    chat_history: List[Dict[str, str]]
    current_part: Literal["part_1", "part_2", "part_3", "evaluation"]
    part_1_question_count: int
    part_3_question_count: int
    main_topic: str
    part_2_cue_card: Optional[CueCard]
    examiner_question: str
    final_feedback: Optional[IeltsFeedback]


# --- Node Definitions ---

async def start_test_node(state: IeltsState) -> dict:
    print("--- NODE: Start Test ---")
    topics = ["Technology", "Environment", "Education", "Travel", "Food", "Health", "Hobbies", "Work", "Relationships"]
    main_topic = random.choice(topics)
    print(f"--- SELECTED TOPIC: {main_topic} ---")
    prompt = ChatPromptTemplate.from_template(
        """You are an expert IELTS examiner starting a speaking test.
        The chosen topic for this session is "{main_topic}".
        Begin the test by introducing yourself and asking the first introductory question related to the main topic.
        Keep the first question simple and welcoming. Your first question:"""
    )
    chain = prompt | llm | StrOutputParser()
    first_question = await chain.ainvoke({"main_topic": main_topic})
    return {
        "main_topic": main_topic,
        "current_part": "part_1",
        "part_1_question_count": 0,
        "part_3_question_count": 0,
        "examiner_question": first_question,
        "chat_history": [{"role": "assistant", "content": first_question}],
    }


async def part_1_node(state: IeltsState) -> dict:
    print("--- NODE: Part 1 ---")

    # Create a NEW list for chat_history to ensure immutability is handled correctly
    # LangGraph state management works best when you return new objects/collections
    # rather than modifying existing ones in place.
    updated_chat_history = list(state["chat_history"])  # Make a copy of the existing history

    # Add the user's response to the new history list
    updated_chat_history.append({"role": "user", "content": state["user_response"]})

    # Increment question count
    new_question_count = state.get("part_1_question_count", 0) + 1

    prompt = ChatPromptTemplate.from_template(
        """You are an IELTS examiner conducting Part 1 of the speaking test. The main topic is "{main_topic}". You have already asked {question_count} questions. Below is the conversation so far.
        Conversation History: {chat_history}
        Ask the NEXT logical, short-answer question related to the main topic. Do not repeat questions. Your next question:"""
    )
    chain = prompt | llm | StrOutputParser()
    next_question = await chain.ainvoke({
        "main_topic": state["main_topic"],
        "question_count": new_question_count,
        "chat_history": updated_chat_history,  # Use the updated history in the prompt
    })

    # Add the examiner's new question to the new history list
    updated_chat_history.append({"role": "assistant", "content": next_question})

    return {
        "examiner_question": next_question,
        "part_1_question_count": new_question_count,
        "chat_history": updated_chat_history,  # Return the new, fully updated history
    }


async def part_2_node(state: IeltsState) -> dict:
    print("--- NODE: Part 2 (Cue Card Generation) ---")
    updated_chat_history = list(state["chat_history"])  # Copy for immutability
    updated_chat_history.append({"role": "user", "content": state["user_response"]})

    parser = PydanticOutputParser(pydantic_object=CueCard)
    prompt = ChatPromptTemplate.from_template(
        """You are an IELTS examiner transitioning to Part 2 of the test. The main topic of the session is "{main_topic}".
        Generate a cue card topic related to the main topic.
        {format_instructions}""",
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    chain = prompt | llm | parser
    cue_card: CueCard = await chain.ainvoke({"main_topic": state["main_topic"]})

    instructions = (
        f"Alright, now we're moving on to Part 2. I'm going to give you a topic...\n\n"
        f"**Your topic is: {cue_card.topic}**\n\n"
        f"You should say:\n"
        f"- {cue_card.points[0]}\n- {cue_card.points[1]}\n- {cue_card.points[2]}\n"
        f"and explain {cue_card.points[3] if len(cue_card.points) > 3 else 'your feelings about it.'}\n\n"
        f"Your preparation time starts now..."
    )
    updated_chat_history.append({"role": "assistant", "content": instructions})
    return {
        "examiner_question": instructions,
        "current_part": "part_2",
        "part_2_cue_card": cue_card.dict(),
        "chat_history": updated_chat_history,
    }


async def part_3_node(state: IeltsState) -> dict:
    print("--- NODE: Part 3 (First Question) ---")
    updated_chat_history = list(state["chat_history"])  # Copy for immutability
    updated_chat_history.append({"role": "user", "content": state["user_response"]})
    cue_card_topic = state["part_2_cue_card"]["topic"]
    prompt = ChatPromptTemplate.from_template(
        """You are an IELTS examiner transitioning to Part 3. You have been discussing the topic: "{cue_card_topic}".
        Now, ask the first abstract, discussion-style question related to this topic. Your first Part 3 question:"""
    )
    chain = prompt | llm | StrOutputParser()
    first_question = await chain.ainvoke({"cue_card_topic": cue_card_topic})
    full_response = f"Thank you. We've been talking about {cue_card_topic}. Now I'd like to ask you one or two more general questions... {first_question}"
    updated_chat_history.append({"role": "assistant", "content": full_response})
    return {
        "examiner_question": full_response,
        "current_part": "part_3",
        "part_3_question_count": 1,
        "chat_history": updated_chat_history,
    }


async def part_3_follow_up_node(state: IeltsState) -> dict:
    print("--- NODE: Part 3 (Follow-up) ---")
    updated_chat_history = list(state["chat_history"])  # Copy for immutability
    updated_chat_history.append({"role": "user", "content": state["user_response"]})
    cue_card_topic = state["part_2_cue_card"]["topic"]
    prompt = ChatPromptTemplate.from_template(
        """You are an IELTS examiner in the middle of Part 3. The main topic is "{cue_card_topic}". Below is the conversation history for Part 3.
        Conversation History: {chat_history}
        Ask the next logical, abstract follow-up question. Your next question:"""
    )
    chain = prompt | llm | StrOutputParser()
    next_question = await chain.ainvoke({"cue_card_topic": cue_card_topic, "chat_history": updated_chat_history})
    updated_chat_history.append({"role": "assistant", "content": next_question})
    return {
        "examiner_question": next_question,
        "part_3_question_count": state["part_3_question_count"] + 1,
        "chat_history": updated_chat_history,
    }


async def evaluation_node(state: IeltsState) -> dict:
    print("--- NODE: Evaluation ---")
    updated_chat_history = list(state["chat_history"])  # Copy for immutability
    updated_chat_history.append({"role": "user", "content": state["user_response"]})
    parser = PydanticOutputParser(pydantic_object=IeltsFeedback)
    prompt = ChatPromptTemplate.from_template(
        """You are an expert IELTS examiner providing detailed feedback based on the entire conversation transcript.
        Analyze the transcript based on official IELTS criteria...
        Full Conversation Transcript: {chat_history}
        {format_instructions}""",
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    chain = prompt | llm | parser
    feedback: IeltsFeedback = await chain.ainvoke({"chat_history": updated_chat_history})
    final_message = (
        "That is the end of the speaking test. Thank you.\n\nHere is your feedback:\n\n"
        f"**Overall Band Score Estimate:** {feedback.overall_band_score}\n\n"
        f"**Fluency and Coherence:**\n{feedback.fluency_and_coherence}\n\n"
        f"**Lexical Resource:**\n{feedback.lexical_resource}\n\n"
        f"**Grammatical Range and Accuracy:**\n{feedback.grammatical_range_and_accuracy}\n\n"
        f"**Final Summary:**\n{feedback.final_summary}"
    )
    return {
        "examiner_question": final_message,
        "current_part": "evaluation",
        "final_feedback": feedback.dict()
    }


# --- Conditional Logic for Branching ---

def route_to_part(state: IeltsState) -> str:
    """
    Routes the graph to the correct starting node for the current turn
    based on the `current_part` in the state.
    """
    print("--- ROUTER: Determining entry point ---")
    part = state.get("current_part")

    if not part:
        print("--- DECISION: New test, starting at start_test ---")
        return "start_test"

    if part == "part_1":
        print("--- DECISION: User is in Part 1, routing to part_1_questions ---")
        return "part_1_questions"

    if part == "part_2":
        print("--- DECISION: User finished Part 2 talk, routing to part_3_first_question ---")
        return "part_3_first_question"

    if part == "part_3":
        print("--- DECISION: User is in Part 3, routing to part_3_follow_up ---")
        return "part_3_follow_up"

    # Default fallback if state is somehow corrupted
    return "start_test"


def route_after_part_1(state: IeltsState) -> Literal["continue_part_1", "move_to_part_2"]:
    # Check if part_1_question_count is properly initialized, default to 0
    if state.get("part_1_question_count", 0) >= 3:
        return "move_to_part_2"
    else:
        return "continue_part_1"


def route_after_part_3(state: IeltsState) -> Literal["continue_part_3", "evaluate"]:
    # Check if part_3_question_count is properly initialized, default to 0
    if state.get("part_3_question_count", 0) >= 3:
        return "evaluate"
    else:
        return "continue_part_3"


# --- Graph Assembly ---

def build_ielts_graph():
    workflow = StateGraph(IeltsState)

    workflow.add_node("start_test", start_test_node)
    workflow.add_node("part_1_questions", part_1_node)
    workflow.add_node("part_2_cue_card", part_2_node)
    workflow.add_node("part_3_first_question", part_3_node)
    workflow.add_node("part_3_follow_up", part_3_follow_up_node)
    workflow.add_node("evaluate", evaluation_node)

    workflow.set_conditional_entry_point(
        route_to_part,
        {
            "start_test": "start_test",
            "part_1_questions": "part_1_questions",  # Mapped to actual node name
            "part_3_first_question": "part_3_first_question",  # Mapped to actual node name
            "part_3_follow_up": "part_3_follow_up",  # Mapped to actual node name
        }
    )

    workflow.add_edge("start_test", END)

    workflow.add_conditional_edges(
        "part_1_questions",
        route_after_part_1,
        {"continue_part_1": END, "move_to_part_2": "part_2_cue_card"}
    )
    workflow.add_edge("part_2_cue_card", END)

    workflow.add_conditional_edges(
        "part_3_first_question",
        route_after_part_3,
        {"continue_part_3": END, "evaluate": "evaluate"}
    )
    workflow.add_conditional_edges(
        "part_3_follow_up",
        route_after_part_3,
        {"continue_part_3": END, "evaluate": "evaluate"}
    )

    workflow.add_edge("evaluate", END)

    graph = workflow.compile()
    return graph