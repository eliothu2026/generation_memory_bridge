"""TimelineCrew: 流水线 A — 逻辑/时间线大纲整理.

提供三个独立的单任务 Crew：增量更新 / 轻量整理 / 全量重跑，
分别对应 NarratorFlow 中的更新节奏（每段 / 每5段 / 每10段）。
"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from narrator_flow.llm_compat import get_deepseek_llm
from narrator_flow.state import LogicOutlineState


@CrewBase
class TimelineCrew:
    """口述史时间线整理 Crew。"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def timeline_organizer(self) -> Agent:
        return Agent(
            config=self.agents_config["timeline_organizer"],
            llm=get_deepseek_llm(),
            verbose=True,
        )

    @task
    def incremental_update_task(self) -> Task:
        return Task(
            config=self.tasks_config["incremental_update_task"],
            output_pydantic=LogicOutlineState,
        )

    @task
    def refine_task(self) -> Task:
        return Task(
            config=self.tasks_config["refine_task"],
            output_pydantic=LogicOutlineState,
        )

    @task
    def full_rerun_task(self) -> Task:
        return Task(
            config=self.tasks_config["full_rerun_task"],
            output_pydantic=LogicOutlineState,
        )

    @crew
    def incremental_crew(self) -> Crew:
        return Crew(
            agents=[self.timeline_organizer()],
            tasks=[self.incremental_update_task()],
            process=Process.sequential,
            verbose=True,
        )

    @crew
    def refine_crew(self) -> Crew:
        return Crew(
            agents=[self.timeline_organizer()],
            tasks=[self.refine_task()],
            process=Process.sequential,
            verbose=True,
        )

    @crew
    def full_rerun_crew(self) -> Crew:
        return Crew(
            agents=[self.timeline_organizer()],
            tasks=[self.full_rerun_task()],
            process=Process.sequential,
            verbose=True,
        )
