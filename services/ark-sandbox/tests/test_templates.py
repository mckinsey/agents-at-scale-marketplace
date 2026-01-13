"""Tests for Argo WorkflowTemplates - validates YAML structure."""

import pytest
import yaml
import os
from pathlib import Path

# Get the templates directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def get_template_files():
    """Get all YAML template files."""
    return list(TEMPLATES_DIR.glob("*.yaml"))


class TestTemplateYAMLValidity:
    """Test that all templates are valid YAML."""
    
    @pytest.mark.parametrize("template_file", get_template_files(), ids=lambda f: f.name)
    def test_template_is_valid_yaml(self, template_file):
        """Test that template file is valid YAML."""
        with open(template_file) as f:
            content = yaml.safe_load(f)
        
        assert content is not None, f"{template_file.name} is empty or invalid"
    
    @pytest.mark.parametrize("template_file", get_template_files(), ids=lambda f: f.name)
    def test_template_has_required_fields(self, template_file):
        """Test that template has required WorkflowTemplate fields."""
        with open(template_file) as f:
            content = yaml.safe_load(f)
        
        # Check apiVersion
        assert content.get("apiVersion") == "argoproj.io/v1alpha1", \
            f"{template_file.name} should have apiVersion: argoproj.io/v1alpha1"
        
        # Check kind
        assert content.get("kind") == "WorkflowTemplate", \
            f"{template_file.name} should have kind: WorkflowTemplate"
        
        # Check metadata.name
        assert content.get("metadata", {}).get("name"), \
            f"{template_file.name} should have metadata.name"
        
        # Check spec.templates
        assert content.get("spec", {}).get("templates"), \
            f"{template_file.name} should have spec.templates"


class TestTemplateStructure:
    """Test template structure and conventions."""
    
    def test_create_sandbox_template(self):
        """Test create-sandbox template structure."""
        with open(TEMPLATES_DIR / "create-sandbox.yaml") as f:
            content = yaml.safe_load(f)
        
        assert content["metadata"]["name"] == "ark-sandbox-create"
        
        templates = content["spec"]["templates"]
        assert len(templates) >= 1
        
        create_template = templates[0]
        assert create_template["name"] == "create"
        
        # Check inputs
        inputs = create_template.get("inputs", {})
        param_names = [p["name"] for p in inputs.get("parameters", [])]
        assert "image" in param_names
        assert "ttl-minutes" in param_names
        assert "pvc-name" in param_names
        assert "namespace" in param_names
        
        # Check outputs
        outputs = create_template.get("outputs", {})
        output_names = [p["name"] for p in outputs.get("parameters", [])]
        assert "sandbox-id" in output_names
        assert "sandbox-namespace" in output_names
        
        # Check resource action
        assert create_template.get("resource", {}).get("action") == "create"
    
    def test_delete_sandbox_template(self):
        """Test delete-sandbox template structure."""
        with open(TEMPLATES_DIR / "delete-sandbox.yaml") as f:
            content = yaml.safe_load(f)
        
        assert content["metadata"]["name"] == "ark-sandbox-delete"
        
        templates = content["spec"]["templates"]
        delete_template = templates[0]
        
        # Check inputs
        inputs = delete_template.get("inputs", {})
        param_names = [p["name"] for p in inputs.get("parameters", [])]
        assert "sandbox-id" in param_names
        assert "namespace" in param_names
        
        # Check resource action
        assert delete_template.get("resource", {}).get("action") == "delete"
    
    def test_wait_sandbox_template(self):
        """Test wait-sandbox template structure."""
        with open(TEMPLATES_DIR / "wait-sandbox.yaml") as f:
            content = yaml.safe_load(f)
        
        assert content["metadata"]["name"] == "ark-sandbox-wait"
        
        templates = content["spec"]["templates"]
        wait_template = templates[0]
        
        # Check inputs
        inputs = wait_template.get("inputs", {})
        param_names = [p["name"] for p in inputs.get("parameters", [])]
        assert "sandbox-id" in param_names
        assert "namespace" in param_names
    
    def test_exec_sandbox_template(self):
        """Test exec-in-sandbox template structure."""
        with open(TEMPLATES_DIR / "exec-in-sandbox.yaml") as f:
            content = yaml.safe_load(f)
        
        assert content["metadata"]["name"] == "ark-sandbox-exec"
        
        templates = content["spec"]["templates"]
        exec_template = templates[0]
        
        # Check inputs
        inputs = exec_template.get("inputs", {})
        param_names = [p["name"] for p in inputs.get("parameters", [])]
        assert "sandbox-id" in param_names
        assert "command" in param_names
        assert "namespace" in param_names
        
        # Check outputs
        outputs = exec_template.get("outputs", {})
        output_names = [p["name"] for p in outputs.get("parameters", [])]
        assert "stdout" in output_names
        assert "exit-code" in output_names
    
    def test_claim_sandbox_template(self):
        """Test claim-sandbox template structure."""
        with open(TEMPLATES_DIR / "claim-sandbox.yaml") as f:
            content = yaml.safe_load(f)
        
        assert content["metadata"]["name"] == "ark-sandbox-claim"
        
        templates = content["spec"]["templates"]
        claim_template = templates[0]
        
        # Check inputs
        inputs = claim_template.get("inputs", {})
        param_names = [p["name"] for p in inputs.get("parameters", [])]
        assert "pool-name" in param_names
        assert "namespace" in param_names
        
        # Check outputs
        outputs = claim_template.get("outputs", {})
        output_names = [p["name"] for p in outputs.get("parameters", [])]
        assert "sandbox-id" in output_names


class TestTemplateNamingConventions:
    """Test that templates follow naming conventions."""
    
    @pytest.mark.parametrize("template_file", get_template_files(), ids=lambda f: f.name)
    def test_template_name_prefix(self, template_file):
        """Test that all templates have ark-sandbox- prefix."""
        with open(template_file) as f:
            content = yaml.safe_load(f)
        
        name = content["metadata"]["name"]
        assert name.startswith("ark-sandbox-"), \
            f"Template name '{name}' should start with 'ark-sandbox-'"
    
    @pytest.mark.parametrize("template_file", get_template_files(), ids=lambda f: f.name)
    def test_template_has_description(self, template_file):
        """Test that templates have description annotations."""
        with open(template_file) as f:
            content = yaml.safe_load(f)
        
        annotations = content.get("metadata", {}).get("annotations", {})
        assert "workflows.argoproj.io/description" in annotations, \
            f"{template_file.name} should have a description annotation"


