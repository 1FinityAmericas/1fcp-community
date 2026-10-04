"""
Data models for validation results.
Provides structured output for Kubernetes resource validation.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum
from datetime import datetime


class ValidationStatus(Enum):
    """Validation status enumeration."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WARNING = "warning"


@dataclass
class ValidationResult:
    """
    Result of a single validation check.
    
    Attributes:
        passed: Whether the validation passed
        resource_type: Type of Kubernetes resource (Pod, Deployment, Node, etc.)
        resource_name: Name of the resource
        namespace: Namespace of the resource (or 'cluster' for cluster-scoped)
        message: Human-readable result message
        details: Additional details dictionary
        timestamp: When the validation was performed
    """
    passed: bool
    resource_type: str
    resource_name: str
    namespace: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def status(self) -> ValidationStatus:
        """Get validation status as enum."""
        return ValidationStatus.PASSED if self.passed else ValidationStatus.FAILED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "passed": self.passed,
            "status": self.status.value,
            "resource_type": self.resource_type,
            "resource_name": self.resource_name,
            "namespace": self.namespace,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }
    
    def __str__(self) -> str:
        status = "✓" if self.passed else "✗"
        return f"[{status}] {self.resource_type}/{self.resource_name} ({self.namespace}): {self.message}"


@dataclass
class ValidationSummary:
    """
    Summary of multiple validation results.
    
    Attributes:
        results: List of individual validation results
        name: Name of the validation run
        started_at: When validation started
        completed_at: When validation completed
    """
    results: List[ValidationResult] = field(default_factory=list)
    name: str = "Validation Run"
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    @property
    def total(self) -> int:
        """Total number of validations."""
        return len(self.results)
    
    @property
    def passed_count(self) -> int:
        """Number of passed validations."""
        return sum(1 for r in self.results if r.passed)
    
    @property
    def failed_count(self) -> int:
        """Number of failed validations."""
        return sum(1 for r in self.results if not r.passed)
    
    @property
    def is_healthy(self) -> bool:
        """True if all validations passed."""
        return self.failed_count == 0
    
    @property
    def pass_rate(self) -> float:
        """Percentage of passed validations."""
        if self.total == 0:
            return 100.0
        return (self.passed_count / self.total) * 100
    
    def add_result(self, result: ValidationResult) -> None:
        """Add a validation result."""
        self.results.append(result)
    
    def complete(self) -> None:
        """Mark validation as complete."""
        self.completed_at = datetime.now()
    
    def get_failed(self) -> List[ValidationResult]:
        """Get list of failed validations."""
        return [r for r in self.results if not r.passed]
    
    def get_passed(self) -> List[ValidationResult]:
        """Get list of passed validations."""
        return [r for r in self.results if r.passed]
    
    def filter_by_resource_type(self, resource_type: str) -> List[ValidationResult]:
        """Filter results by resource type."""
        return [r for r in self.results if r.resource_type == resource_type]
    
    def filter_by_namespace(self, namespace: str) -> List[ValidationResult]:
        """Filter results by namespace."""
        return [r for r in self.results if r.namespace == namespace]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "total": self.total,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "pass_rate": f"{self.pass_rate:.1f}%",
            "is_healthy": self.is_healthy,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "results": [r.to_dict() for r in self.results]
        }
    
    def __str__(self) -> str:
        status = "HEALTHY" if self.is_healthy else "UNHEALTHY"
        return (
            f"{self.name}: {status}\n"
            f"Total: {self.total} | Passed: {self.passed_count} | "
            f"Failed: {self.failed_count} | Pass Rate: {self.pass_rate:.1f}%"
        )
    
    def print_report(self) -> str:
        """Generate a detailed report string."""
        lines = [
            "=" * 60,
            f"VALIDATION REPORT: {self.name}",
            "=" * 60,
            f"Status: {'HEALTHY' if self.is_healthy else 'UNHEALTHY'}",
            f"Total Checks: {self.total}",
            f"Passed: {self.passed_count}",
            f"Failed: {self.failed_count}",
            f"Pass Rate: {self.pass_rate:.1f}%",
            "-" * 60,
        ]
        
        if self.failed_count > 0:
            lines.append("FAILED CHECKS:")
            for result in self.get_failed():
                lines.append(f"  {result}")
            lines.append("-" * 60)
        
        lines.append("ALL CHECKS:")
        for result in self.results:
            lines.append(f"  {result}")
        
        lines.append("=" * 60)
        return "\n".join(lines)
