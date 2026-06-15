"""AnchorCrew: 流水线 C — 叙事锚定物 + 图像生成提示词."""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from narrator_flow.llm_compat import get_deepseek_llm
from narrator_flow.state import AnchorObjectState


@CrewBase
class AnchorCrew:
    """叙事锚点物件与图像提示词 Crew。

    提供两个独立的单任务 Crew：
    - incremental_crew：每个 chunk 都跑一次的增量细化
    - full_regen_crew：当 prompt_detail_score 达到阈值时触发的全量重写
    """

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def anchor_curator(self) -> Agent:
        return Agent(
            config=self.agents_config["anchor_curator"],
            llm=get_deepseek_llm(),
            verbose=True,
        )

    @task
    def anchor_incremental_task(self) -> Task:
        return Task(
            config=self.tasks_config["anchor_incremental_task"],
            output_pydantic=AnchorObjectState,
        )

    @task
    def anchor_full_regen_task(self) -> Task:
        return Task(
            config=self.tasks_config["anchor_full_regen_task"],
            output_pydantic=AnchorObjectState,
        )

    @crew
    def incremental_crew(self) -> Crew:
        return Crew(
            agents=[self.anchor_curator()],
            tasks=[self.anchor_incremental_task()],
            process=Process.sequential,
            verbose=True,
        )

    @crew
    def full_regen_crew(self) -> Crew:
        return Crew(
            agents=[self.anchor_curator()],
            tasks=[self.anchor_full_regen_task()],
            process=Process.sequential,
            verbose=True,
        )
