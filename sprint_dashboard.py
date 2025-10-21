"""
Sprint/Iteration Analytics Dashboard

Provides sprint metrics, burndown calculations, and health analysis.
"""

from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import streamlit as st


class SprintAnalytics:
    """Analytics engine for sprint/iteration data"""

    def __init__(self, work_items: List[Dict], iteration_data: Dict = None):
        """
        Initialize sprint analytics.

        Args:
            work_items: List of work items in the sprint
            iteration_data: Iteration metadata (start/end dates, name, etc.)
        """
        self.work_items = work_items
        self.iteration_data = iteration_data or {}

    def calculate_metrics(self) -> Dict:
        """
        Calculate key sprint metrics.

        Returns:
            dict: Sprint metrics including story points, completion rates, etc.
        """
        total_items = len(self.work_items)
        if total_items == 0:
            return self._empty_metrics()

        # Story Points
        total_points = 0
        completed_points = 0

        # Work Item States
        state_counts = {'New': 0, 'Active': 0, 'Resolved': 0, 'Closed': 0, 'Other': 0}
        type_counts = {}
        assignee_counts = {}

        # Analyze each work item
        for wi in self.work_items:
            fields = wi.get('fields', {})

            # Story Points
            points = fields.get('Microsoft.VSTS.Scheduling.StoryPoints', 0) or 0
            total_points += points

            # Check if completed
            state = fields.get('System.State', 'Unknown')
            if state.lower() in ['closed', 'done', 'resolved']:
                completed_points += points

            # State counts
            if state in state_counts:
                state_counts[state] += 1
            else:
                state_counts['Other'] += 1

            # Type counts
            wi_type = fields.get('System.WorkItemType', 'Unknown')
            type_counts[wi_type] = type_counts.get(wi_type, 0) + 1

            # Assignee counts
            assigned_to = fields.get('System.AssignedTo', {})
            if isinstance(assigned_to, dict):
                assignee_name = assigned_to.get('displayName', 'Unassigned')
            else:
                assignee_name = 'Unassigned'
            assignee_counts[assignee_name] = assignee_counts.get(assignee_name, 0) + 1

        # Calculate completion rates
        completion_rate = (completed_points / total_points * 100) if total_points > 0 else 0
        closed_items = state_counts.get('Closed', 0) + state_counts.get('Resolved', 0)
        item_completion_rate = (closed_items / total_items * 100) if total_items > 0 else 0

        # Sprint timeline
        sprint_progress = self._calculate_sprint_progress()

        return {
            'total_items': total_items,
            'closed_items': closed_items,
            'total_points': total_points,
            'completed_points': completed_points,
            'remaining_points': total_points - completed_points,
            'completion_rate': round(completion_rate, 1),
            'item_completion_rate': round(item_completion_rate, 1),
            'state_counts': state_counts,
            'type_counts': type_counts,
            'assignee_counts': assignee_counts,
            'sprint_progress': sprint_progress,
            'health_status': self._calculate_health_status(completion_rate, sprint_progress)
        }

    def _empty_metrics(self) -> Dict:
        """Return empty metrics structure"""
        return {
            'total_items': 0,
            'closed_items': 0,
            'total_points': 0,
            'completed_points': 0,
            'remaining_points': 0,
            'completion_rate': 0,
            'item_completion_rate': 0,
            'state_counts': {},
            'type_counts': {},
            'assignee_counts': {},
            'sprint_progress': {'days_elapsed': 0, 'days_remaining': 0, 'days_total': 0, 'progress_pct': 0},
            'health_status': 'unknown'
        }

    def _calculate_sprint_progress(self) -> Dict:
        """Calculate sprint timeline progress"""
        if not self.iteration_data:
            return {'days_elapsed': 0, 'days_remaining': 0, 'days_total': 0, 'progress_pct': 0}

        # Parse dates
        start_date_str = self.iteration_data.get('attributes', {}).get('startDate')
        end_date_str = self.iteration_data.get('attributes', {}).get('finishDate')

        if not start_date_str or not end_date_str:
            return {'days_elapsed': 0, 'days_remaining': 0, 'days_total': 0, 'progress_pct': 0}

        try:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            today = datetime.now(start_date.tzinfo)

            days_total = (end_date - start_date).days
            days_elapsed = max(0, (today - start_date).days)
            days_remaining = max(0, (end_date - today).days)

            progress_pct = (days_elapsed / days_total * 100) if days_total > 0 else 0

            return {
                'days_elapsed': days_elapsed,
                'days_remaining': days_remaining,
                'days_total': days_total,
                'progress_pct': round(progress_pct, 1),
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            }
        except Exception:
            return {'days_elapsed': 0, 'days_remaining': 0, 'days_total': 0, 'progress_pct': 0}

    def _calculate_health_status(self, completion_rate: float, sprint_progress: Dict) -> str:
        """
        Calculate sprint health status.

        Args:
            completion_rate: % of story points completed
            sprint_progress: Sprint timeline data

        Returns:
            str: 'green', 'yellow', 'red', or 'unknown'
        """
        progress_pct = sprint_progress.get('progress_pct', 0)

        # If sprint hasn't started or no data
        if progress_pct == 0:
            return 'unknown'

        # Ideal: completion should be >= sprint progress
        if completion_rate >= progress_pct:
            return 'green'  # On track or ahead

        # Warning: completion is behind but not critically
        if completion_rate >= progress_pct * 0.7:
            return 'yellow'  # Slightly behind

        # Critical: significantly behind schedule
        return 'red'  # At risk

    def generate_burndown_data(self) -> Tuple[List, List]:
        """
        Generate burndown chart data.

        Returns:
            tuple: (ideal_burndown, actual_burndown) lists of story points
        """
        metrics = self.calculate_metrics()
        total_points = metrics['total_points']
        completed_points = metrics['completed_points']
        sprint_progress = metrics['sprint_progress']

        days_total = sprint_progress.get('days_total', 10)
        days_elapsed = sprint_progress.get('days_elapsed', 0)

        if days_total == 0:
            return [], []

        # Ideal burndown (linear)
        ideal_burndown = []
        for day in range(days_total + 1):
            remaining = total_points * (1 - day / days_total)
            ideal_burndown.append(max(0, remaining))

        # Actual burndown (simplified - shows current progress)
        actual_burndown = []
        # For simplicity, we'll show linear progress to current point
        # In real implementation, you'd track daily completion from work item history
        remaining_points = total_points - completed_points

        for day in range(days_elapsed + 1):
            if days_elapsed > 0:
                burned = completed_points * (day / days_elapsed)
                actual_burndown.append(max(0, total_points - burned))
            else:
                actual_burndown.append(total_points)

        # Project future based on current velocity
        if days_elapsed > 0 and days_elapsed < days_total:
            velocity = completed_points / days_elapsed
            for day in range(days_elapsed + 1, days_total + 1):
                remaining = total_points - (velocity * day)
                actual_burndown.append(max(0, remaining))

        return ideal_burndown, actual_burndown

    def get_work_items_table_data(self) -> List[Dict]:
        """
        Format work items for table display.

        Returns:
            list: Work items formatted for st.dataframe
        """
        table_data = []

        for wi in self.work_items:
            fields = wi.get('fields', {})

            # Extract assignee
            assigned_to = fields.get('System.AssignedTo', {})
            if isinstance(assigned_to, dict):
                assignee_name = assigned_to.get('displayName', 'Unassigned')
            else:
                assignee_name = 'Unassigned'

            # Extract story points
            story_points = fields.get('Microsoft.VSTS.Scheduling.StoryPoints', 0) or 0

            table_data.append({
                'ID': wi.get('id'),
                'Type': fields.get('System.WorkItemType', 'Unknown'),
                'Title': fields.get('System.Title', 'Untitled'),
                'State': fields.get('System.State', 'Unknown'),
                'Assigned To': assignee_name,
                'Story Points': story_points,
                'Priority': fields.get('Microsoft.VSTS.Common.Priority', 'N/A')
            })

        return table_data

    def generate_ai_summary_context(self) -> str:
        """
        Generate context for AI sprint analysis.

        Returns:
            str: Formatted context for LiteLLM
        """
        metrics = self.calculate_metrics()

        context_parts = []

        context_parts.append(f"**Sprint Overview**")
        context_parts.append(f"- Total Work Items: {metrics['total_items']}")
        context_parts.append(f"- Closed Work Items: {metrics['closed_items']}")
        context_parts.append(f"- Total Story Points: {metrics['total_points']}")
        context_parts.append(f"- Completed Story Points: {metrics['completed_points']}")
        context_parts.append(f"- Completion Rate: {metrics['completion_rate']}%")
        context_parts.append(f"- Health Status: {metrics['health_status'].upper()}")

        sprint_progress = metrics['sprint_progress']
        context_parts.append(f"\n**Sprint Timeline**")
        context_parts.append(f"- Days Elapsed: {sprint_progress.get('days_elapsed', 0)}")
        context_parts.append(f"- Days Remaining: {sprint_progress.get('days_remaining', 0)}")
        context_parts.append(f"- Sprint Progress: {sprint_progress.get('progress_pct', 0)}%")

        context_parts.append(f"\n**Work Item Breakdown by State**")
        for state, count in metrics['state_counts'].items():
            if count > 0:
                context_parts.append(f"- {state}: {count}")

        context_parts.append(f"\n**Work Item Breakdown by Type**")
        for wi_type, count in metrics['type_counts'].items():
            context_parts.append(f"- {wi_type}: {count}")

        # Identify risks
        context_parts.append(f"\n**Potential Risks**")
        if metrics['health_status'] == 'red':
            context_parts.append("- ⚠️ Sprint is significantly behind schedule")
        elif metrics['health_status'] == 'yellow':
            context_parts.append("- ⚠️ Sprint is slightly behind schedule")

        if metrics['state_counts'].get('New', 0) > metrics['closed_items']:
            context_parts.append("- ⚠️ Many work items are still in 'New' state")

        return "\n".join(context_parts)

    def generate_burnup_data(self) -> Tuple[List, List]:
        """
        Generate burnup chart data (work completed over time).

        Returns:
            tuple: (total_scope, completed_work) lists showing scope and completion
        """
        metrics = self.calculate_metrics()
        total_points = metrics['total_points']
        completed_points = metrics['completed_points']
        sprint_progress = metrics['sprint_progress']

        days_total = sprint_progress.get('days_total', 10)
        days_elapsed = sprint_progress.get('days_elapsed', 0)

        if days_total == 0:
            return [], []

        # Total scope line (assuming no scope changes for now)
        total_scope = [total_points] * (days_total + 1)

        # Completed work line (shows accumulation)
        completed_work = []
        for day in range(days_elapsed + 1):
            if days_elapsed > 0:
                completed = completed_points * (day / days_elapsed)
                completed_work.append(completed)
            else:
                completed_work.append(0)

        # Project future based on velocity
        if days_elapsed > 0 and days_elapsed < days_total:
            velocity = completed_points / days_elapsed
            for day in range(days_elapsed + 1, days_total + 1):
                projected = min(total_points, velocity * day)
                completed_work.append(projected)

        return total_scope, completed_work


class MultiSprintAnalytics:
    """Analytics for comparing multiple sprints"""

    def __init__(self, sprints_data: List[Dict]):
        """
        Initialize multi-sprint analytics.

        Args:
            sprints_data: List of dicts with 'sprint_info' and 'work_items'
        """
        self.sprints_data = sprints_data

    def calculate_velocity_trends(self) -> Dict:
        """
        Calculate velocity trends across sprints.

        Returns:
            dict: Velocity metrics and trends
        """
        sprint_velocities = []
        sprint_names = []

        for sprint_data in self.sprints_data:
            sprint_info = sprint_data.get('sprint_info', {})
            work_items = sprint_data.get('work_items', [])

            analytics = SprintAnalytics(work_items, sprint_info)
            metrics = analytics.calculate_metrics()

            sprint_names.append(sprint_info.get('name', 'Unknown'))
            sprint_velocities.append(metrics['completed_points'])

        avg_velocity = sum(sprint_velocities) / len(sprint_velocities) if sprint_velocities else 0

        return {
            'sprint_names': sprint_names,
            'velocities': sprint_velocities,
            'average_velocity': round(avg_velocity, 1),
            'trend': self._calculate_trend(sprint_velocities)
        }

    def _calculate_trend(self, velocities: List[float]) -> str:
        """Calculate if velocity is increasing, decreasing, or stable"""
        if len(velocities) < 2:
            return 'stable'

        recent_avg = sum(velocities[-3:]) / len(velocities[-3:])
        older_avg = sum(velocities[:-3]) / len(velocities[:-3]) if len(velocities) > 3 else velocities[0]

        if recent_avg > older_avg * 1.1:
            return 'increasing'
        elif recent_avg < older_avg * 0.9:
            return 'decreasing'
        else:
            return 'stable'

    def compare_sprints(self) -> Dict:
        """
        Compare key metrics across sprints.

        Returns:
            dict: Comparison data for all sprints
        """
        comparison_data = {
            'sprint_names': [],
            'total_points': [],
            'completed_points': [],
            'completion_rates': [],
            'total_items': [],
            'closed_items': []
        }

        for sprint_data in self.sprints_data:
            sprint_info = sprint_data.get('sprint_info', {})
            work_items = sprint_data.get('work_items', [])

            analytics = SprintAnalytics(work_items, sprint_info)
            metrics = analytics.calculate_metrics()

            comparison_data['sprint_names'].append(sprint_info.get('name', 'Unknown'))
            comparison_data['total_points'].append(metrics['total_points'])
            comparison_data['completed_points'].append(metrics['completed_points'])
            comparison_data['completion_rates'].append(metrics['completion_rate'])
            comparison_data['total_items'].append(metrics['total_items'])
            comparison_data['closed_items'].append(metrics['closed_items'])

        return comparison_data

    def predict_completion(self, remaining_points: float, current_velocity: float) -> Dict:
        """
        Predict sprint completion based on current velocity.

        Args:
            remaining_points: Story points remaining
            current_velocity: Current velocity (points per day)

        Returns:
            dict: Prediction data including days needed, confidence
        """
        if current_velocity == 0:
            return {
                'days_needed': float('inf'),
                'can_complete': False,
                'confidence': 'low',
                'message': 'No velocity detected yet'
            }

        days_needed = remaining_points / current_velocity

        # Calculate confidence based on historical velocity
        avg_velocity = self.calculate_velocity_trends()['average_velocity']
        velocity_variance = abs(current_velocity - avg_velocity) / avg_velocity if avg_velocity > 0 else 1

        if velocity_variance < 0.2:
            confidence = 'high'
        elif velocity_variance < 0.4:
            confidence = 'medium'
        else:
            confidence = 'low'

        return {
            'days_needed': round(days_needed, 1),
            'can_complete': days_needed <= 10,  # Assuming 10 days in sprint
            'confidence': confidence,
            'message': f'Estimated {days_needed:.1f} days to complete remaining work'
        }
