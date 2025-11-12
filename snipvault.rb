# Homebrew formula for SnipVault
class Snipvault < Formula
  include Language::Python::Virtualenv

  desc "LLM-Powered Code Snippet Manager with vector search"
  homepage "https://github.com/ARTHURFLECK1828/snipvault"
  url "https://github.com/ARTHURFLECK1828/snipvault/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "REPLACE_WITH_ACTUAL_SHA256"
  license "MIT"
  head "https://github.com/ARTHURFLECK1828/snipvault.git", branch: "main"

  depends_on "python@3.11"
  depends_on "postgresql@15"

  resource "click" do
    url "https://files.pythonhosted.org/packages/source/c/click/click-8.1.7.tar.gz"
    sha256 "ca9853ad459e787e2192211578cc907e7594e294c7ccc834310722b41b9ca6de"
  end

  resource "psycopg2-binary" do
    url "https://files.pythonhosted.org/packages/source/p/psycopg2-binary/psycopg2_binary-2.9.9.tar.gz"
    sha256 "7f01846810177d829c7692f1f5ada8096762d9172af1b1a28d4ab5b77c923c1c"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/source/r/rich/rich-13.7.0.tar.gz"
    sha256 "5cb5123b5cf9ee70584244246816e9114227e0b98ad9176eede6ad54bf5403fa"
  end

  # Add more resources as needed

  def install
    virtualenv_install_with_resources
  end

  def post_install
    # Create configuration directory
    (var/"snipvault").mkpath
    (var/"snipvault/logs").mkpath
    (var/"snipvault/cache").mkpath
  end

  def caveats
    <<~EOS
      SnipVault requires PostgreSQL and Pinecone API keys to function.

      1. Start PostgreSQL:
         brew services start postgresql@15

      2. Create database:
         createdb snipvault

      3. Set environment variables in ~/.zshrc or ~/.bashrc:
         export POSTGRES_HOST=localhost
         export POSTGRES_DB=snipvault
         export POSTGRES_USER=#{ENV["USER"]}
         export PINECONE_API_KEY=your_pinecone_key
         export PINECONE_ENVIRONMENT=your_pinecone_env
         export GEMINI_API_KEY=your_gemini_key

      4. Initialize SnipVault:
         snipvault init

      For more information, visit:
      https://github.com/ARTHURFLECK1828/snipvault#readme
    EOS
  end

  test do
    assert_match "SnipVault", shell_output("#{bin}/snipvault --version")
  end
end
