"""
AI analysis engine using OpenAI and Anthropic.
"""
from typing import List, Dict, Any, Optional
import time
from openai import AsyncOpenAI
import anthropic

from app.config import settings
from app.utils.logger import setup_logger
from app.utils.errors import AIError

logger = setup_logger(__name__)


class AIEngine:
    """Service for AI-powered document analysis."""
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY) if settings.ANTHROPIC_API_KEY else None
        self.default_model = settings.DEFAULT_AI_MODEL
        self.fallback_model = settings.AI_FALLBACK_MODEL
        self.temperature = settings.AI_TEMPERATURE
    
    async def analyze_document_chunk(
        self,
        chunk_text: str,
        document_type: str,
        chunk_index: int,
        total_chunks: int,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a single document chunk.
        
        Args:
            chunk_text: Text content of chunk
            document_type: Type of document (contract, nda, etc.)
            chunk_index: Current chunk index
            total_chunks: Total number of chunks
            model: AI model to use (optional)
            
        Returns:
            Analysis result dictionary
        """
        model = model or self.default_model
        
        prompt = self._build_analysis_prompt(chunk_text, document_type, chunk_index, total_chunks)
        
        try:
            if model.startswith("gpt-") or model.startswith("o1-"):
                result = await self._call_openai(prompt, model)
            elif model.startswith("claude-"):
                result = await self._call_anthropic(prompt, model)
            else:
                # Default to OpenAI
                result = await self._call_openai(prompt, self.default_model)
            
            return result
            
        except Exception as e:
            logger.error(f"AI analysis failed for chunk {chunk_index}: {e}")
            # Try fallback if available
            if model != self.fallback_model and self.anthropic_client:
                logger.info(f"Trying fallback model: {self.fallback_model}")
                try:
                    return await self._call_anthropic(prompt, self.fallback_model)
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")
                    raise AIError(f"AI analysis failed: {str(e)}")
            raise AIError(f"AI analysis failed: {str(e)}")
    
    async def _call_openai(self, prompt: str, model: str) -> Dict[str, Any]:
        """Call OpenAI API."""
        try:
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a legal document analyst. Provide structured JSON responses."},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"} if "gpt-4" in model else None,
            )
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            # Parse JSON response
            import json
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # If not JSON, wrap in structure
                result = {"analysis": content, "raw": True}
            
            return {
                "result": result,
                "tokens_used": tokens_used,
                "model": model,
            }
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def _call_anthropic(self, prompt: str, model: str) -> Dict[str, Any]:
        """Call Anthropic API."""
        if not self.anthropic_client:
            raise AIError("Anthropic API key not configured")
        
        try:
            # Anthropic uses sync API, so we need to run in executor
            import asyncio
            
            def _call():
                return self.anthropic_client.messages.create(
                    model=model,
                    max_tokens=4096,
                    temperature=self.temperature,
                    messages=[
                        {"role": "user", "content": prompt},
                    ],
                )
            
            response = await asyncio.to_thread(_call)
            
            content = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            
            # Parse JSON response
            import json
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                result = {"analysis": content, "raw": True}
            
            return {
                "result": result,
                "tokens_used": tokens_used,
                "model": model,
            }
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    def _build_analysis_prompt(
        self,
        chunk_text: str,
        document_type: str,
        chunk_index: int,
        total_chunks: int,
    ) -> str:
        """Build analysis prompt for AI."""
        return f"""Analyze this legal document chunk ({chunk_index + 1} of {total_chunks}).

Document Type: {document_type}

Document Text:
{chunk_text}

Please provide a JSON response with the following structure:
{{
  "parties": [{{"name": "...", "role": "...", "contact": "..."}}],
  "dates": [{{"type": "...", "date": "...", "description": "..."}}],
  "financial_terms": [{{"type": "...", "amount": 0.0, "currency": "USD", "frequency": "..."}}],
  "obligations": [{{"party": "...", "obligation": "...", "deadline": "..."}}],
  "risks": [{{"severity": "high|medium|low", "title": "...", "description": "...", "recommendation": "...", "page_reference": null}}],
  "missing_clauses": ["..."],
  "unusual_terms": ["..."],
  "summary": "Brief summary of this chunk"
}}

Focus on:
1. Identifying all parties and their roles
2. Extracting all dates, deadlines, and important timeframes
3. Finding financial terms (amounts, payment schedules, penalties)
4. Listing obligations for each party
5. Flagging potential risks (unusual clauses, missing protections, ambiguous language)
6. Identifying missing standard clauses for this document type
7. Noting any non-standard or unusual terms

Be thorough and accurate. If information is not present in this chunk, use empty arrays.
"""

    async def generate_summary(
        self,
        all_chunk_analyses: List[Dict[str, Any]],
        document_type: str,
    ) -> str:
        """
        Generate executive summary from all chunk analyses.
        
        Args:
            all_chunk_analyses: List of analysis results from all chunks
            document_type: Type of document
            
        Returns:
            Executive summary text (2-3 paragraphs)
        """
        # Combine all analyses
        combined_data = self._combine_chunk_analyses(all_chunk_analyses)
        
        summary_prompt = f"""Based on the complete analysis of this {document_type} document, write a comprehensive 2-3 paragraph executive summary.

Key Findings:
- Parties: {len(combined_data.get('parties', []))} parties identified
- Dates: {len(combined_data.get('dates', []))} important dates
- Financial Terms: {len(combined_data.get('financial_terms', []))} financial terms
- Risks: {len([r for r in combined_data.get('risks', []) if r.get('severity') == 'high'])} high-risk items

Provide a clear, professional summary that:
1. Identifies the document type and main purpose
2. Highlights key parties and their roles
3. Summarizes critical terms, dates, and obligations
4. Flags the most significant risks and concerns
5. Notes any missing standard protections

Write in clear, professional language suitable for legal professionals.
"""
        
        try:
            if self.default_model.startswith("gpt-"):
                response = await self.openai_client.chat.completions.create(
                    model=self.default_model,
                    messages=[
                        {"role": "system", "content": "You are a legal document analyst writing executive summaries."},
                        {"role": "user", "content": summary_prompt},
                    ],
                    temperature=0.5,
                )
                return response.choices[0].message.content
            else:
                # Use Anthropic
                import asyncio
                response = await asyncio.to_thread(
                    lambda: self.anthropic_client.messages.create(
                        model=self.fallback_model,
                        max_tokens=1000,
                        messages=[{"role": "user", "content": summary_prompt}],
                    )
                )
                return response.content[0].text
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            # Fallback to simple summary
            return self._generate_fallback_summary(combined_data, document_type)
    
    def _combine_chunk_analyses(self, chunk_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine analyses from all chunks, deduplicating."""
        combined = {
            "parties": [],
            "dates": [],
            "financial_terms": [],
            "obligations": [],
            "risks": [],
            "missing_clauses": [],
            "unusual_terms": [],
        }
        
        seen_parties = set()
        seen_dates = set()
        seen_risks = set()
        seen_clauses = set()
        seen_terms = set()
        
        for chunk_result in chunk_analyses:
            analysis = chunk_result.get("result", {})
            
            # Combine parties (deduplicate by name+role)
            for party in analysis.get("parties", []):
                key = (party.get("name", ""), party.get("role", ""))
                if key not in seen_parties:
                    combined["parties"].append(party)
                    seen_parties.add(key)
            
            # Combine dates (deduplicate by type+date)
            for date_item in analysis.get("dates", []):
                key = (date_item.get("type", ""), date_item.get("date", ""))
                if key not in seen_dates:
                    combined["dates"].append(date_item)
                    seen_dates.add(key)
            
            # Combine financial terms
            combined["financial_terms"].extend(analysis.get("financial_terms", []))
            
            # Combine obligations
            combined["obligations"].extend(analysis.get("obligations", []))
            
            # Combine risks (deduplicate by title)
            for risk in analysis.get("risks", []):
                title = risk.get("title", "")
                if title not in seen_risks:
                    combined["risks"].append(risk)
                    seen_risks.add(title)
            
            # Combine missing clauses (deduplicate)
            for clause in analysis.get("missing_clauses", []):
                if clause not in seen_clauses:
                    combined["missing_clauses"].append(clause)
                    seen_clauses.add(clause)
            
            # Combine unusual terms (deduplicate)
            for term in analysis.get("unusual_terms", []):
                if term not in seen_terms:
                    combined["unusual_terms"].append(term)
                    seen_terms.add(term)
        
        return combined
    
    def _generate_fallback_summary(self, combined_data: Dict[str, Any], document_type: str) -> str:
        """Generate a simple fallback summary if AI fails."""
        parties_count = len(combined_data.get("parties", []))
        risks_count = len(combined_data.get("risks", []))
        high_risks = len([r for r in combined_data.get("risks", []) if r.get("severity") == "high"])
        
        return f"""This {document_type} document involves {parties_count} parties and contains {risks_count} identified risks, including {high_risks} high-severity items. 

Key financial terms, dates, and obligations have been extracted and are detailed in the full analysis. {high_risks} critical risk items require immediate attention.

Please review the complete analysis report for detailed findings and recommendations.
"""

