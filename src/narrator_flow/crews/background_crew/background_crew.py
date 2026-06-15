"""BackgroundCrew: 流水线 B — 时代/社会背景知识生成（纯增量）."""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from narrator_flow.llm_compat import get_deepseek_llm
from narrator_flow.state import BackgroundKnowledgeState


@CrewBase
class BackgroundCrew:
    """时代背景知识 Crew，每个 chunk 都以纯增量方式调用一次。"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def background_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["background_researcher"],
            llm=get_deepseek_llm(),
            verbose=True,
        )

    @task
    def incremental_background_task(self) -> Task:
        return Task(
            config=self.tasks_config["incremental_background_task"],
            output_pydantic=BackgroundKnowledgeState,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.background_researcher()],
            tasks=[self.incremental_background_task()],
            process=Process.sequential,
            verbose=True,
        )
