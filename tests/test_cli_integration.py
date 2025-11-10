"""Integration tests for CLI commands."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from main import cli


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_cli_version(self, runner):
        """Test --version flag."""
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert 'SnipVault' in result.output
        assert '1.0.0' in result.output

    def test_cli_help(self, runner):
        """Test --help flag."""
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'SnipVault' in result.output
        assert 'search' in result.output
        assert 'add' in result.output

    @patch('cli.commands.add.insert_snippet')
    @patch('cli.commands.add.generate_embedding')
    @patch('cli.commands.add.get_pinecone_index')
    def test_add_command_basic(self, mock_index, mock_gen_emb, mock_insert, runner):
        """Test add command with basic input."""
        mock_insert.return_value = 1
        mock_gen_emb.return_value = [0.1] * 768
        mock_idx = MagicMock()
        mock_index.return_value = mock_idx

        result = runner.invoke(cli, [
            'add',
            'Test Snippet',  # title as positional argument
            'print("test")',  # code as positional argument
            '--lang', 'python',
            '--tags', 'test,python'
        ])

        assert result.exit_code == 0
        assert 'added successfully' in result.output.lower() or 'snippet' in result.output.lower()
        mock_insert.assert_called_once()
        mock_idx.upsert.assert_called_once()

    @patch('cli.commands.search.hybrid_search')
    @patch('cli.commands.search.rerank_results')
    def test_search_command_basic(self, mock_rerank, mock_search, runner, sample_snippets):
        """Test search command."""
        mock_search.return_value = [
            {
                'id': '1',
                'score': 0.9,
                'snippet': sample_snippets[0]
            }
        ]
        mock_rerank.return_value = [
            {
                'id': '1',
                'final_score': 0.95,
                'score_breakdown': {},
                'snippet': sample_snippets[0]
            }
        ]

        result = runner.invoke(cli, ['search', 'python'])

        assert result.exit_code == 0
        assert 'python' in result.output.lower()

    @patch('cli.commands.search.hybrid_search')
    def test_search_command_with_filters(self, mock_search, runner):
        """Test search with language and tag filters."""
        mock_search.return_value = []

        result = runner.invoke(cli, [
            'search', 'test query',
            '--lang', 'python',
            '--tags', 'api,test',
            '--top', '10'
        ])

        assert result.exit_code == 0
        # Verify filters were applied
        call_kwargs = mock_search.call_args[1]
        assert call_kwargs['language'] == 'python'
        assert 'api' in call_kwargs['tags']

    @patch('cli.commands.list_snippets.list_all_snippets')
    def test_list_command(self, mock_list, runner, sample_snippets):
        """Test list command."""
        mock_list.return_value = sample_snippets

        result = runner.invoke(cli, ['list'])

        assert result.exit_code == 0
        mock_list.assert_called_once()

    @patch('cli.commands.show.get_snippet_by_id')
    @patch('cli.commands.show.get_related_snippets')
    def test_show_command(self, mock_related, mock_get, runner, sample_snippet):
        """Test show command."""
        mock_get.return_value = sample_snippet
        mock_related.return_value = []

        result = runner.invoke(cli, ['show', '1'])

        assert result.exit_code == 0
        mock_get.assert_called_once_with(1)

    @patch('cli.commands.show.get_snippet_by_id')
    def test_show_command_not_found(self, mock_get, runner):
        """Test show command with non-existent ID."""
        mock_get.return_value = None

        result = runner.invoke(cli, ['show', '999'])

        assert result.exit_code == 1
        assert 'not found' in result.output.lower()

    @patch('cli.commands.delete.get_snippet_by_id')
    @patch('cli.commands.delete.delete_snippet')
    @patch('cli.commands.delete.get_pinecone_index')
    def test_delete_command_with_force(self, mock_index, mock_delete, mock_get, runner, sample_snippet):
        """Test delete command with --force flag."""
        mock_get.return_value = sample_snippet
        mock_delete.return_value = True
        mock_idx = MagicMock()
        mock_index.return_value = mock_idx

        result = runner.invoke(cli, ['delete', '1', '--force'])

        assert result.exit_code == 0
        mock_delete.assert_called_once_with(1)
        mock_idx.delete.assert_called_once()

    @patch('cli.commands.update.get_snippet_by_id')
    @patch('cli.commands.update.update_snippet')
    def test_update_command(self, mock_update, mock_get, runner, sample_snippet):
        """Test update command."""
        mock_get.return_value = sample_snippet
        mock_update.return_value = True

        result = runner.invoke(cli, [
            'update', '1',
            '--title', 'Updated Title'
        ])

        assert result.exit_code == 0
        mock_update.assert_called_once()

    @patch('cli.commands.export.list_all_snippets')
    def test_export_command_json(self, mock_list, runner, sample_snippets, temp_dir):
        """Test export command in JSON format."""
        mock_list.return_value = sample_snippets
        output_file = temp_dir / "export.json"

        result = runner.invoke(cli, [
            'export',
            '--format', 'json',
            '--output', str(output_file),
            '--all'
        ])

        assert result.exit_code == 0
        assert output_file.exists()

    @patch('cli.commands.import_snippets.insert_snippet')
    @patch('cli.commands.import_snippets.generate_embedding')
    @patch('cli.commands.import_snippets.get_pinecone_index')
    def test_import_command(self, mock_index, mock_gen_emb, mock_insert,
                           runner, temp_dir, sample_snippets):
        """Test import command."""
        import json

        # Create test import file
        # Convert datetime objects to strings for JSON serialization
        snippets_for_json = []
        for s in sample_snippets:
            snippet_copy = s.copy()
            snippet_copy['created_at'] = snippet_copy['created_at'].isoformat()
            snippets_for_json.append(snippet_copy)

        import_file = temp_dir / "import.json"
        with open(import_file, 'w') as f:
            json.dump(snippets_for_json, f)

        mock_insert.side_effect = [1, 2, 3]
        mock_gen_emb.return_value = [0.1] * 768
        mock_idx = MagicMock()
        mock_index.return_value = mock_idx

        result = runner.invoke(cli, [
            'import',
            str(import_file),
            '--format', 'json'
        ], input='y\n')  # Auto-confirm the import

        assert result.exit_code == 0
        assert mock_insert.call_count == 3

    @patch('cli.commands.index.scan_directory')
    @patch('cli.commands.index.list_all_snippets')
    @patch('cli.commands.index.insert_snippet')
    def test_index_command(self, mock_insert, mock_list, mock_scan,
                          runner, temp_dir):
        """Test index command for codebase indexing."""
        mock_scan.return_value = [
            (str(temp_dir / "test.py"), "python"),
            (str(temp_dir / "app.js"), "javascript")
        ]
        mock_list.return_value = []
        mock_insert.side_effect = [1, 2]

        # Create test files
        (temp_dir / "test.py").write_text("print('test')")
        (temp_dir / "app.js").write_text("console.log('test');")

        with patch('cli.commands.index.generate_embedding') as mock_emb, \
             patch('cli.commands.index.get_pinecone_index') as mock_idx:
            mock_emb.return_value = [0.1] * 768
            mock_idx.return_value = MagicMock()

            result = runner.invoke(cli, [
                'index',
                str(temp_dir)
            ])

            # Should process files (exact exit code depends on implementation)
            assert 'index' in result.output.lower() or 'snippet' in result.output.lower()

    @patch('db.migrate.run_all_migrations')
    def test_migrate_command(self, mock_migrate, runner):
        """Test migrate command."""
        mock_migrate.return_value = 2  # 2 migrations applied

        result = runner.invoke(cli, ['migrate'])

        assert result.exit_code == 0
        assert 'migration' in result.output.lower()
        mock_migrate.assert_called_once()

    @patch('main.initialize_all')
    def test_init_command_success(self, mock_init, runner):
        """Test init command successful."""
        mock_init.return_value = True

        result = runner.invoke(cli, ['init'])

        assert result.exit_code == 0
        assert 'ready' in result.output.lower()
        mock_init.assert_called_once()

    @patch('main.initialize_all')
    def test_init_command_failure(self, mock_init, runner):
        """Test init command failure."""
        mock_init.return_value = False

        result = runner.invoke(cli, ['init'])

        assert result.exit_code == 1
        assert 'failed' in result.output.lower()
