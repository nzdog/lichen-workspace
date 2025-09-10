"""Command-line interface for Lichen Chunker."""

import sys
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .io_utils import find_files
from .pipeline import create_pipeline
from .schema_validation import validate_protocol_file

app = typer.Typer(help="Lichen Protocol Chunker - Chunk and embed Lichen Protocol JSONs")
console = Console()


@app.command()
def validate(
    files: List[Path] = typer.Argument(..., help="Protocol JSON files to validate"),
    schema: Optional[Path] = typer.Option(None, "--schema", "-s", help="Path to schema file")
):
    """Validate protocol JSON files against schema."""
    if not files:
        console.print("[red]No files provided[/red]")
        raise typer.Exit(1)
    
    table = Table(title="Validation Results")
    table.add_column("File", style="cyan")
    table.add_column("Valid", style="green")
    table.add_column("Errors", style="red")
    
    all_valid = True
    
    for file_path in files:
        if not file_path.exists():
            table.add_row(str(file_path), "❌", "File not found")
            all_valid = False
            continue
        
        is_valid, errors, _ = validate_protocol_file(file_path, schema)
        
        if is_valid:
            table.add_row(str(file_path), "✅", "Valid")
        else:
            table.add_row(str(file_path), "❌", "; ".join(errors))
            all_valid = False
    
    console.print(table)
    
    if not all_valid:
        raise typer.Exit(1)


@app.command()
def chunk(
    files: List[Path] = typer.Argument(..., help="Protocol JSON files to chunk"),
    output_dir: Path = typer.Option(Path("./data"), "--output", "-o", help="Output directory for chunks"),
    max_tokens: int = typer.Option(600, "--max-tokens", help="Maximum tokens per chunk"),
    overlap: int = typer.Option(60, "--overlap", help="Overlap tokens between chunks"),
    schema: Optional[Path] = typer.Option(None, "--schema", "-s", help="Path to schema file")
):
    """Chunk protocol JSON files into sections."""
    if not files:
        console.print("[red]No files provided[/red]")
        raise typer.Exit(1)
    
    pipeline = create_pipeline(max_tokens=max_tokens, overlap_tokens=overlap)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Chunking files...", total=len(files))
        
        results = []
        for file_path in files:
            if not file_path.exists():
                console.print(f"[red]File not found: {file_path}[/red]")
                continue
            
            result = pipeline.process_file(file_path, output_dir, schema)
            results.append(result)
            progress.advance(task)
    
    # Display results
    table = Table(title="Chunking Results")
    table.add_column("File", style="cyan")
    table.add_column("Valid", style="green")
    table.add_column("Chunks", style="blue")
    table.add_column("Output", style="yellow")
    table.add_column("Error", style="red")
    
    for result in results:
        if result.valid:
            table.add_row(
                result.file_path,
                "✅",
                str(result.chunks_created),
                result.chunks_file or "",
                ""
            )
        else:
            table.add_row(
                result.file_path,
                "❌",
                "0",
                "",
                result.error_message or "Unknown error"
            )
    
    console.print(table)


@app.command()
def embed(
    chunks_files: List[Path] = typer.Argument(..., help="Chunk JSONL files to embed"),
    backend: str = typer.Option("auto", "--backend", "-b", help="Embedding backend (openai, sbert, auto)"),
    index_path: Path = typer.Option(Path("./index"), "--index", "-i", help="Index directory")
):
    """Embed chunks and build FAISS index."""
    if not chunks_files:
        console.print("[red]No chunk files provided[/red]")
        raise typer.Exit(1)
    
    pipeline = create_pipeline(backend=backend, index_path=index_path)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Embedding chunks...", total=len(chunks_files))
        
        for chunks_file in chunks_files:
            if not chunks_file.exists():
                console.print(f"[red]File not found: {chunks_file}[/red]")
                continue
            
            pipeline.embed_chunks([chunks_file])
            progress.advance(task)
    
    # Save index
    pipeline.save_index()
    
    # Display stats
    stats = pipeline.get_stats()
    console.print(f"[green]Index created with {stats['total_chunks']} chunks[/green]")
    console.print(f"Backend: {stats['embedding_backend']}")
    console.print(f"Dimension: {stats['embedding_dimension']}")


@app.command()
def index(
    embedded_files: List[Path] = typer.Option([], "--files", "-f", help="Embedded JSONL files"),
    backend: str = typer.Option("auto", "--backend", "-b", help="Embedding backend"),
    index_path: Path = typer.Option(Path("./index"), "--index", "-i", help="Index directory"),
    rebuild: bool = typer.Option(False, "--rebuild", help="Rebuild index from scratch")
):
    """Build or update FAISS index."""
    pipeline = create_pipeline(backend=backend, index_path=index_path)
    
    if rebuild:
        pipeline.clear_index()
        console.print("[yellow]Rebuilding index...[/yellow]")
    
    if embedded_files:
        pipeline.embed_chunks(embedded_files)
    else:
        console.print("[red]No files provided[/red]")
        raise typer.Exit(1)
    
    pipeline.save_index()
    
    stats = pipeline.get_stats()
    console.print(f"[green]Index updated with {stats['total_chunks']} chunks[/green]")


@app.command()
def process(
    files: List[Path] = typer.Argument(..., help="Protocol JSON files to process"),
    backend: str = typer.Option("auto", "--backend", "-b", help="Embedding backend (openai, sbert, auto)"),
    max_tokens: int = typer.Option(600, "--max-tokens", help="Maximum tokens per chunk"),
    overlap: int = typer.Option(60, "--overlap", help="Overlap tokens between chunks"),
    output_dir: Path = typer.Option(Path("./data"), "--output", "-o", help="Output directory for chunks"),
    index_path: Path = typer.Option(Path("./index"), "--index", "-i", help="Index directory"),
    schema: Optional[Path] = typer.Option(None, "--schema", "-s", help="Path to schema file")
):
    """Process protocol files end-to-end (validate, chunk, embed, index)."""
    if not files:
        console.print("[red]No files provided[/red]")
        raise typer.Exit(1)
    
    pipeline = create_pipeline(
        backend=backend,
        max_tokens=max_tokens,
        overlap_tokens=overlap,
        index_path=index_path
    )
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Processing files...", total=len(files))
        
        results = []
        for file_path in files:
            if not file_path.exists():
                console.print(f"[red]File not found: {file_path}[/red]")
                continue
            
            result = pipeline.process_file(file_path, output_dir, schema)
            results.append(result)
            progress.advance(task)
    
    # Save index
    pipeline.save_index()
    
    # Display results
    table = Table(title="Processing Results")
    table.add_column("File", style="cyan")
    table.add_column("Valid", style="green")
    table.add_column("Chunks", style="blue")
    table.add_column("Output", style="yellow")
    table.add_column("Error", style="red")
    
    total_chunks = 0
    valid_count = 0
    
    for result in results:
        if result.valid:
            table.add_row(
                result.file_path,
                "✅",
                str(result.chunks_created),
                result.chunks_file or "",
                ""
            )
            total_chunks += result.chunks_created
            valid_count += 1
        else:
            table.add_row(
                result.file_path,
                "❌",
                "0",
                "",
                result.error_message or "Unknown error"
            )
    
    console.print(table)
    
    # Display summary
    stats = pipeline.get_stats()
    console.print(f"\n[green]Summary:[/green]")
    console.print(f"Files processed: {len(files)}")
    console.print(f"Valid files: {valid_count}")
    console.print(f"Total chunks: {total_chunks}")
    console.print(f"Index chunks: {stats['total_chunks']}")
    console.print(f"Backend: {stats['embedding_backend']}")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    k: int = typer.Option(5, "--top-k", help="Number of results to return"),
    index_path: Path = typer.Option(Path("./index"), "--index", "-i", help="Index directory"),
    backend: str = typer.Option("auto", "--backend", "-b", help="Embedding backend")
):
    """Search the index."""
    pipeline = create_pipeline(backend=backend, index_path=index_path)
    
    results = pipeline.search(query, k)
    
    if not results:
        console.print("[yellow]No results found[/yellow]")
        return
    
    table = Table(title=f"Search Results for: {query}")
    table.add_column("Score", style="blue")
    table.add_column("Protocol", style="cyan")
    table.add_column("Section", style="green")
    table.add_column("Preview", style="white")
    
    for result in results:
        table.add_row(
            f"{result.score:.3f}",
            result.metadata.title,
            result.metadata.section_name,
            result.text_preview[:100] + "..." if len(result.text_preview) > 100 else result.text_preview
        )
    
    console.print(table)


@app.command()
def stats(
    index_path: Path = typer.Option(Path("./index"), "--index", "-i", help="Index directory"),
    backend: str = typer.Option("auto", "--backend", "-b", help="Embedding backend")
):
    """Show index statistics."""
    pipeline = create_pipeline(backend=backend, index_path=index_path)
    stats = pipeline.get_stats()
    
    table = Table(title="Index Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    for key, value in stats.items():
        table.add_row(key.replace("_", " ").title(), str(value))
    
    console.print(table)


if __name__ == "__main__":
    app()

