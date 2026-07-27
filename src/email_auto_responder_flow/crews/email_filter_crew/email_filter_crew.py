from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, TavilySearchTool
from langchain_openai import ChatOpenAI

from email_auto_responder_flow.tools.gmail_tools import CreateDraftTool, GmailGetThreadTool


@CrewBase
class EmailFilterCrew:
    """Email Filter Crew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    llm = ChatOpenAI(model="gpt-4o")

    @agent
    def email_filter_agent(self) -> Agent:
        search_tool = SerperDevTool()
        return Agent(
            config=self.agents_config["email_filter_agent"],
            tools=[search_tool],
            llm=self.llm,
            verbose=True,
            allow_delegation=True,
        )

    @agent
    def email_action_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["email_action_agent"],
            llm=self.llm,
            verbose=True,
            tools=[
                GmailGetThreadTool(),
                TavilySearchTool(),
            ],
        )

    @agent
    def email_response_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["email_response_writer"],
            llm=self.llm,
            verbose=True,
            tools=[
                TavilySearchTool(),
                GmailGetThreadTool(),
                CreateDraftTool(),
            ],
        )

    @task
    def filter_emails_task(self) -> Task:
        return Task(config=self.tasks_config["filter_emails"])

    @task
    def action_required_emails_task(self) -> Task:
        return Task(config=self.tasks_config["action_required_emails"])

    @task
    def draft_responses_task(self) -> Task:
        return Task(config=self.tasks_config["draft_responses"])

    @crew
    def crew(self) -> Crew:
        """Creates the Email Filter Crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
