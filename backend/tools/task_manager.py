
# ==========================================
# astra_engine/tools/task_manager.py
# ==========================================

import json
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class TaskManager:
    """
    Manage tasks, todos, and reminders.
    Stores in memory.json under "tasks" key.
    """

    def __init__(self, memory: Dict):
        self.memory = memory
        if "tasks" not in self.memory:
            self.memory["tasks"] = []

    def add_task(self, title: str, deadline: str = None, priority: str = "medium") -> Dict:
        """Add a new task."""
        task = {
            "id": self._generate_id(),
            "title": title,
            "status": "todo",
            "priority": priority,
            "deadline": deadline,
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": None
        }
        self.memory["tasks"].append(task)
        logger.info(f"✓ Added task: {title}")
        
        return {
            "success": True,
            "task": task,
            "message": f"Added task: {title}"
        }

    def list_tasks(self, status: str = None) -> Dict:
        """List all tasks or filter by status."""
        tasks = self.memory["tasks"]
        
        if status:
            tasks = [t for t in tasks if t["status"] == status]

        # Sort by priority then deadline
        priority_order = {"high": 0, "medium": 1, "low": 2}
        tasks = sorted(tasks, key=lambda t: (
            priority_order.get(t["priority"], 1),
            t["deadline"] or "9999"
        ))

        return {
            "success": True,
            "tasks": tasks,
            "count": len(tasks)
        }

    def complete_task(self, task_id: str) -> Dict:
        """Mark task as complete."""
        for task in self.memory["tasks"]:
            if task["id"] == task_id:
                task["status"] = "done"
                task["completed_at"] = datetime.utcnow().isoformat()
                logger.info(f"✓ Completed task: {task['title']}")
                return {
                    "success": True,
                    "task": task,
                    "message": f"Completed: {task['title']}"
                }
        
        return {"success": False, "error": "Task not found"}

    def remove_task(self, task_id: str) -> Dict:
        """Remove a task."""
        original_count = len(self.memory["tasks"])
        self.memory["tasks"] = [t for t in self.memory["tasks"] if t["id"] != task_id]
        
        if len(self.memory["tasks"]) < original_count:
            return {"success": True, "message": "Task removed"}
        
        return {"success": False, "error": "Task not found"}

    def _generate_id(self) -> str:
        """Generate unique task ID."""
        import uuid
        return str(uuid.uuid4())[:8]