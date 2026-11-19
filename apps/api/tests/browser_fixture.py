"""Create a synthetic assignment in the disposable browser test database."""

import os
import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.admin import catalog_service, cohort_service, schemas
from app.modules.delivery.models import Cohort
from app.modules.identity.deps import Principal
from app.modules.identity.models import User


def main() -> None:
    if os.environ.get("LLM_MODE") != "fixture":
        raise RuntimeError("Browser fixtures require the test stack")
    engine = create_engine(get_settings().migration_database_url)
    with Session(engine) as db, db.begin():
        users = {
            user.email: user.id
            for user in db.scalars(
                select(User).where(
                    User.email.in_(
                        ["admin@example.com", "trainer@example.com", "intern.ba@example.com"]
                    )
                )
            )
        }
        admin = Principal(users["admin@example.com"], frozenset({"admin"}))
        course = catalog_service.create_course(
            db,
            admin,
            schemas.CourseIn(
                title=f"Browser review test {uuid.uuid4().hex[:8]}", role_profile="ba"
            ),
        )
        for index in range(1, 10):
            tree = catalog_service.create_module(
                db,
                admin,
                course.id,
                schemas.ModuleIn(
                    title=f"Milestone {index}",
                    description="Browser fixture",
                    learning_objective="Review a task",
                ),
            )
            module_id = tree.modules[-1].id
            tree = catalog_service.create_task(
                db,
                admin,
                module_id,
                schemas.TaskIn(
                    title=f"Requirements test {index}",
                    description="Describe the policy search flow",
                    deliverables=[
                        schemas.DeliverableIn(id="notes", title="Requirements", kind=["text"])
                    ],
                ),
            )
            if index == 1:
                task_id = tree.modules[-1].tasks[0].id
                catalog_service.save_rubric_draft(
                    db,
                    admin,
                    task_id,
                    schemas.RubricDraftIn(
                        criteria=[
                            schemas.CriterionIn(
                                id="acceptance",
                                title="Acceptance criteria",
                                weight=100,
                                levels={
                                    "0": "Missing",
                                    "1": "Vague",
                                    "2": "Partial",
                                    "3": "Observable",
                                    "4": "Includes the alternate path",
                                },
                                correction_template="State an observable result when a policy search has no answer.",
                            )
                        ]
                    ),
                )
                catalog_service.publish_rubric(db, admin, task_id)
        catalog_service.update_course(
            db, admin, course.id, schemas.CoursePatch(review_status="approved")
        )
        cohort = Cohort(name="Browser review cohort", trainer_id=users["trainer@example.com"])
        db.add(cohort)
        db.flush()
        cohort_service.enroll(
            db,
            admin,
            cohort.id,
            schemas.EnrollmentIn(user_id=users["intern.ba@example.com"], course_id=course.id),
        )


if __name__ == "__main__":
    main()
