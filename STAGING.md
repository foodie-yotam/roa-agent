# Staging Branch

This is the **staging branch** for the ROA Voice Agent.

## Purpose

This branch is configured for auto-deployment to LangGraph Cloud/LangSmith for experimentation and testing purposes.

## Workflow

- **Staging Branch**: CEO and team can experiment with new features and configurations
- **Production Branch (main)**: Stable, consolidated features after testing in staging
- **Deployment**: This branch auto-deploys on commit to LangGraph Cloud

## Making Changes

Feel free to experiment with:
- Agent configurations
- New tools and capabilities
- Prompt modifications
- Graph structure changes

Changes will be consolidated into the production branch after validation.

## Notes

- All commits to this branch trigger automatic deployment
- Test thoroughly before merging to main
- Keep the main branch stable for production use
